import asyncio
import json
import os
import sys
from pathlib import Path

from timeit import default_timer as timer

import boto3
import boto3.session
import botocore

from .profiler import timed


# After research and benchmarking 64 seems to be the best speed without big
# trade-offs.
MAX_THREAD_CHECK_S3 = 32
MAX_THREAD_UPLOAD_S3 = 32
MIN_CHUNK_SIZE_CHECK_S3 = 100
MIN_CHUNK_SIZE_UPLOAD_S3 = 200


class EndOfStreamError(Exception):
    pass


async def map_async(func, it, worker_count, qsize=0):
    in_queue, out_queue = asyncio.Queue(qsize), asyncio.Queue(qsize)

    async def feeder():
        try:
            for item in it:
                await in_queue.put((item, None))
        except Exception as e:
            await in_queue.put((None, e))
        finally:
            for _ in range(worker_count):
                await in_queue.put((None, EndOfStreamError()))

    async def worker():
        while True:
            work, err = await in_queue.get()
            if err is not None:
                await out_queue.put((None, err))
                if isinstance(err, EndOfStreamError):
                    break
            else:
                result = None
                try:
                    result = await func(work)
                except Exception as e:
                    err = e
                finally:
                    await out_queue.put((result, err))

    workers_complete = 0
    for _ in range(worker_count):
        asyncio.create_task(worker())
    asyncio.create_task(feeder())
    while workers_complete < worker_count:
        result, err = await out_queue.get()
        if isinstance(err, EndOfStreamError):
            workers_complete += 1
            continue
        yield (result, err)


def to_chunks(it, chunk_size):
    a = []
    for item in it:
        a.append(item)
        if len(a) == chunk_size:  # pragma: no cover
            yield a
            a = []
    if 0 < len(a) < chunk_size:
        yield a


def slash_join(*args):
    """ join url parts safely """
    return "/".join(arg.strip("/") for arg in args)


@timed
def is_s3_folder_empty(aws_key, aws_secret, aws_session_token, bucket, key):
    """ check if s3 folder is empty or not existing """
    result = False
    session = boto3.session.Session()
    s3_client = session.client(
        's3',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        aws_session_token=aws_session_token)
    prefix = key
    if prefix[-1] != '/':
        prefix = prefix + '/'
    try:
        response = s3_client.list_objects(
            Bucket=bucket, Prefix=prefix, Delimiter='/')
        if 'Contents' not in response:
            result = True  # folder is empty
    except botocore.exceptions.ClientError as e:  # pragma: no cover
        print('That should not happen. Empty folder check should not cause '
              'a boto ClientError.')
        raise (e)
    return result


def check_s3_existence(aws_key, aws_secret, aws_session_token, bucket,
                       resources, disable_check=False):
    """ check if resource is already existing or needs uploading """

    def s3_md5sum(s3_client, bucket_name, resource_name):
        """ get (special) md5 of S3 resource or None when not existing """
        try:
            md5sum = s3_client.head_object(
                Bucket=bucket_name,
                Key=resource_name
            )['ETag']
        except botocore.exceptions.ClientError:  # pragma: no cover
            md5sum = None
        return md5sum

    def update_resource(resource, data):
        resource['mime_type'] = data['mime_type']
        resource['width'] = data['width']
        resource['height'] = data['height']
        return resource

    if disable_check:
        check_resource = update_resource
    else:
        session = boto3.session.Session()
        s3_client = session.client(
            's3',
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            aws_session_token=aws_session_token)

        def check_s3(resource, data):
            if data['s3_md5'] != s3_md5sum(s3_client, bucket,
                                           resource['output_s3']):
                return update_resource(resource, data)
            else:  # pragma: no cover
                return None

        check_resource = check_s3

    checked_resources = []
    for resource in resources:
        try:
            with open(resource['input_metadata_file']) as json_file:
                data = json.load(json_file)
            checked_resources.append(check_resource(resource, data))
        except FileNotFoundError as e:
            print('Error: No metadata json found!')
            raise (e)
    return checked_resources


def upload_s3(aws_key, aws_secret, aws_session_token, bucket, resources):
    """ upload s3 process for ThreadPoolExecutor """
    # use session for multithreading according to
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html?highlight=multithreading#multithreading-multiprocessing
    session = boto3.session.Session()
    s3_client = session.client(
        's3',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        aws_session_token=aws_session_token)

    keys = []
    for resource in resources:
        key = resource["key"]
        metadata = resource.get("metadata", None)
        extra_args = {
            "ContentType": resource["content_type"]
        }

        if metadata is not None:
            extra_args['Metadata'] = metadata

        s3_client.upload_file(
            Filename=resource["filename"],
            Bucket=bucket,
            Key=key,
            ExtraArgs=extra_args
        )
        keys.append(key)
    return keys


async def upload(in_dir, bucket, bucket_folder):
    """ upload resource and resource json to S3 """

    aws_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_session_token = os.getenv('AWS_SESSION_TOKEN')

    disable_deep_folder_check = is_s3_folder_empty(
        aws_key=aws_key,
        aws_secret=aws_secret,
        aws_session_token=aws_session_token,
        bucket=bucket,
        key=bucket_folder)

    # environment variables mandatory for ThreadPoolExecutor
    if aws_key is None or aws_secret is None:
        raise EnvironmentError(
            'Failed because AWS_ACCESS_KEY_ID and/or AWS_SECRET_ACCESS_KEY '
            'environment variable missing.')

    sha1_filepattern = '?' * 40  # sha1 hexdigest as 40 characters

    # get all resources on file system
    all_resources = []
    for sha1filename in Path(in_dir).glob(sha1_filepattern):
        resource = {}
        resource['bucket'] = bucket
        resource['input_file'] = str(sha1filename)
        resource['input_metadata_file'] = resource['input_file'] + '.json'
        resource['output_s3'] = slash_join(
            bucket_folder, os.path.basename(resource['input_file']))
        resource['output_s3_metadata'] = slash_join(
            bucket_folder,
            os.path.basename(resource['input_file']) + '-unused.json')
        all_resources.append(resource)

    # Check which resources are missing
    start = timer()
    upload_resources = []
    chunk_size = max(
        len(all_resources) // MAX_THREAD_CHECK_S3,
        MIN_CHUNK_SIZE_CHECK_S3
    )
    print(f'Checking resources in chunks of {chunk_size}')

    async def check_s3_existence_worker(resources):
        return await asyncio.to_thread(
            check_s3_existence,
            aws_key=aws_key,
            aws_secret=aws_secret,
            aws_session_token=aws_session_token,
            bucket=bucket,
            resources=resources,
            disable_check=disable_deep_folder_check
        )

    async for checked_resources, err in map_async(
        check_s3_existence_worker,
        to_chunks(all_resources, chunk_size),
        MAX_THREAD_CHECK_S3
    ):
        if err is not None:
            raise err
        for maybe_resource in checked_resources:
            if maybe_resource is not None:
                upload_resources.append(maybe_resource)
                if not disable_deep_folder_check:  # pragma: no cover
                    print(".", end="", flush=True)
            else:
                if not disable_deep_folder_check:  # pragma: no cover
                    print("x", end="", flush=True)

    if disable_deep_folder_check:
        print('- quick checked (destination S3 folder empty or non existing)',
              end='', flush=True)
    print()
    print('{} resources need uploading.'.format(len(upload_resources)))
    elapsed = (timer() - start)
    print('Time it took to check: {}s'.format(elapsed))

    # Upload to s3
    chunk_size = max(
        len(upload_resources) * 2 // MAX_THREAD_UPLOAD_S3,
        MIN_CHUNK_SIZE_UPLOAD_S3
    )
    start = timer()
    upload_count = 0
    print(f'Uploading to S3 in chunks of {chunk_size}', end='', flush=True)

    async def upload_s3_worker(resources):
        return await asyncio.to_thread(
            upload_s3,
            aws_key=aws_key,
            aws_secret=aws_secret,
            aws_session_token=aws_session_token,
            bucket=bucket,
            resources=resources
        )

    def upload_arg_gen():
        for resource in upload_resources:
            # upload metadata first (because this is not checked)
            yield {
                "filename": resource["input_metadata_file"],
                "key": resource["output_s3_metadata"],
                "content_type": "application/json",
            }

            # upload resource file last (existence/md5 is checked)
            yield {
                "filename": resource["input_file"],
                "key": resource["output_s3"],
                "content_type": resource["mime_type"],
                "metadata": (
                    None
                    if resource["width"] == -1 or resource["height"] == -1
                    else {
                        "width": str(resource["width"]),
                        "height": str(resource["height"]),
                    }
                ),
            }

    async for result, err in map_async(
        upload_s3_worker,
        to_chunks(upload_arg_gen(), chunk_size),
        MAX_THREAD_UPLOAD_S3
    ):
        if err is not None:
            raise err
        for maybe_key in result:
            if maybe_key is not None:
                upload_count += 1
                print('.', end='', flush=True)

    # divide by 2, don't count json metadata
    upload_count = int(upload_count / 2)
    print()
    print('{} resources uploaded.'.format(upload_count))
    elapsed = (timer() - start)
    print('Time it took to upload: {}s'.format(elapsed))
    if (upload_count) != len(upload_resources):  # pragma: no cover
        print('ERROR: Uploaded counted and needed to upload mismatch: {} != {}'.format(upload_count,
                                                                                       len(upload_resources)))
        sys.exit(1)
    print('FINISHED uploading resources.')


async def async_main():
    in_dir = Path(sys.argv[1]).resolve(strict=True)
    bucket = sys.argv[2]
    bucket_folder = sys.argv[3]
    await upload(in_dir, bucket, bucket_folder)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":  # pragma: no cover
    main()
