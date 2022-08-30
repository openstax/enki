import concurrent.futures
import json
import os
import sys
import traceback
from pathlib import Path
from timeit import default_timer as timer

import boto3
import boto3.session
import botocore

# After research and benchmarking 64 seems to be the best speed without big
# trade-offs.
MAX_THREAD_CHECK_S3 = 64
MAX_THREAD_UPLOAD_S3 = 64


class ThreadPoolExecutorStackTraced(concurrent.futures.ThreadPoolExecutor):
    # Stack traced ThreadPoolExecutor for better error messages on exceptions
    # on threads https://stackoverflow.com/a/24457608/756056

    def submit(self, fn, *args, **kwargs):
        """Submits the wrapped function instead of `fn`"""

        return super(ThreadPoolExecutorStackTraced, self).submit(
            self._function_wrapper, fn, *args, **kwargs)

    def _function_wrapper(self, fn, *args, **kwargs):
        """Wraps `fn` in order to preserve the traceback of any kind of
        raised exception

        """
        try:
            return fn(*args, **kwargs)
        except Exception:  # pragma: no cover
            # Creates an exception of the same type with the traceback as
            # message
            raise sys.exc_info()[0](traceback.format_exc())


def slash_join(*args):
    """ join url parts safely """
    return "/".join(arg.strip("/") for arg in args)


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


def check_s3_existence(aws_key, aws_secret, aws_session_token, bucket, resource,
                       disable_check=False):
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

    try:
        upload_resource = None
        with open(resource['input_metadata_file']) as json_file:
            data = json.load(json_file)
        if disable_check:
            # empty or non existing s3 folder
            # skip individual s3 file check
            upload_resource = resource
        else:
            session = boto3.session.Session()
            s3_client = session.client(
                's3',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                aws_session_token=aws_session_token)
            if data['s3_md5'] != s3_md5sum(s3_client, bucket,
                                           resource['output_s3']):
                upload_resource = resource

        if upload_resource is not None:
            upload_resource['mime_type'] = data['mime_type']
            upload_resource['width'] = data['width']
            upload_resource['height'] = data['height']

        return upload_resource
    except FileNotFoundError as e:
        print('Error: No metadata json found!')
        raise (e)


def upload_s3(aws_key, aws_secret, aws_session_token,
              filename, bucket, key, content_type, metadata=None):
    """ upload s3 process for ThreadPoolExecutor """
    # use session for multithreading according to
    # https://boto3.amazonaws.com/v1/documentation/api/latest/guide/resources.html?highlight=multithreading#multithreading-multiprocessing
    session = boto3.session.Session()
    s3_client = session.client(
        's3',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        aws_session_token=aws_session_token)

    extra_args = {
        "ContentType": content_type
    }
    if metadata is not None:
        extra_args['Metadata'] = metadata

    s3_client.upload_file(
        Filename=filename,
        Bucket=bucket,
        Key=key,
        ExtraArgs=extra_args
    )
    return key


def upload(in_dir, bucket, bucket_folder):
    """ upload resource and resource json to S3 """

    def halt_all_threads(executor):  # pragma: no cover
        """ halt all threads from executor """
        executor._threads.clear()
        concurrent.futures.thread._threads_queues.clear()

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

    # check which resources are missing (with ThreadPoolExecutor)
    start = timer()
    upload_resources = []
    check_futures = []
    with ThreadPoolExecutorStackTraced(max_workers=MAX_THREAD_CHECK_S3) \
            as executor:
        print('Checking which files to upload ', end='', flush=True)
        for resource in all_resources:
            check_futures.append(
                executor.submit(
                    check_s3_existence,
                    aws_key=aws_key,
                    aws_secret=aws_secret,
                    aws_session_token=aws_session_token,
                    bucket=bucket,
                    resource=resource,
                    disable_check=disable_deep_folder_check)
            )
        for future in concurrent.futures.as_completed(check_futures):
            try:
                resource = future.result()
            except Exception as e:  # pragma: no cover
                print(e)  # print error from ThreadPoolExecutorStackTraced
                halt_all_threads(executor)
                sys.exit(1)
            try:  # pragma: no cover
                # free memory of threads
                check_futures.remove(future)
                del future
                # process thread results
                if resource is not None:
                    upload_resources.append(resource)
                    if not disable_deep_folder_check:
                        print('.', end='', flush=True)
                else:
                    if not disable_deep_folder_check:
                        print('x', end='', flush=True)
            except Exception:  # pragma: no cover
                halt_all_threads(executor)
                raise
    if disable_deep_folder_check:
        print('- quick checked (destination S3 folder empty or non existing)',
              end='', flush=True)
    print()
    print('{} resources need uploading.'.format(len(upload_resources)))
    elapsed = (timer() - start)
    print('Time it took to check: {}s'.format(elapsed))

    # upload to s3 (with ThreadPoolExecutor)
    start = timer()
    upload_count = 0
    upload_futures = []
    with ThreadPoolExecutorStackTraced(max_workers=MAX_THREAD_UPLOAD_S3) \
            as executor:
        print('Uploading to S3 ', end='', flush=True)
        for resource in upload_resources:
            # upload metadata first (because this is not checked)
            upload_futures.append(
                executor.submit(
                    upload_s3,
                    aws_key=aws_key,
                    aws_secret=aws_secret,
                    aws_session_token=aws_session_token,
                    filename=resource['input_metadata_file'],
                    bucket=bucket,
                    key=resource['output_s3_metadata'],
                    content_type='application/json')
            )

            # upload resource file last (existence/md5 is checked)
            metadata = None if resource['width'] == -1 or resource['height'] == -1 \
                else {'width': str(resource['width']), 'height': str(resource['height'])}

            upload_futures.append(
                executor.submit(
                    upload_s3,
                    aws_key=aws_key,
                    aws_secret=aws_secret,
                    aws_session_token=aws_session_token,
                    filename=resource['input_file'],
                    bucket=bucket,
                    key=resource['output_s3'],
                    content_type=resource['mime_type'],
                    metadata=metadata)
            )
        for future in concurrent.futures.as_completed(upload_futures):
            try:
                result = future.result()
            except Exception as e:  # pragma: no cover
                print(e)  # print error from ThreadPoolExecutorStackTraced
                halt_all_threads(executor)
                sys.exit(1)
            try:
                # free memory of threads
                upload_futures.remove(future)
                del future
                # process thread results
                if result is not None:
                    upload_count = upload_count + 1
                    print('.', end='', flush=True)
            except Exception:  # pragma: no cover
                halt_all_threads(executor)
                raise
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


def main():
    in_dir = Path(sys.argv[1]).resolve(strict=True)
    bucket = sys.argv[2]
    bucket_folder = sys.argv[3]
    upload(in_dir, bucket, bucket_folder)


if __name__ == "__main__":  # pragma: no cover
    main()
