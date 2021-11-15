# About

Running `npm run build` will generate Concourse Pipeline YAML files for the following:

- corgi-production.yml
- corgi-staging.yml
- webhosting-production.yml
- webhosting-sandbox.yml

Running `npm run build:local` will generate all of the previous plus the following:

- corgi-local.yml (only for local testing)
- webhosting-local.yml (only for local testing)

The `*-local.yml` files differ in the following ways:

- They can optionally point to a local registry
- They use a random CODE_VERSION for S3 reasons (detecting if a book has already been built) but use `main` for the Docker image version
- The CORGI API Url is http://smocker, a Mock server
- The torpedo code is removed mostly because the Mock server does not have an easy way to change state (queued, processing, complete)


# Install Prerequisites

1. Start up concourse and the Docker registry by running `docker-compose up -d` in this directory (See **Linux Notes** below)
1. Sign in to concourse by visiting http://localhost:8080 and using `test` and `test` for the username/password
1. Download the fly command (into `~/Downloads/fly`)
1. Make it executable by running `chmod 755 ~/Downloads/fly`
1. Authenticate through the commandline by running `~/Downloads/fly --target local login --concourse-url http://localhost:8080` and opening the link that it prints out

Now you can build a pipeline using `npm run build` and upload it to concourse.


# Pipeline.yml Build Alternatives

If you are changing code inside the docker image you will need to upload the image to a local registry (see **Option B**). If you are not editing code inside the image then you can use the [main tag on dockerhub](https://hub.docker.com/r/openstax/richb-press/tags) by following the instructions in **Option A**.

In both cases you will want to set the AWS credentials which will be used to upload to S3 (e.g. `source /path/to/set_aws_creds -r sandbox:full-admin -t ######`).

If you are not testing the upload parts you can provide dummy values for the following:

- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY


## Option A: Use image on DockerHub

Since we are not changing the image we can use the images on dockerhub.
DockerHub does have a rate limit. If you start too many jobs, Concourse will provide a cryptic error.

At that point you can switch to **Option B** or provide your `DOCKERHUB_USERNAME` and `DOCKERHUB_PASSWORD` credentials (as environment variables) when running `npm run build` and those will be injected into the pipeline.yml files. A local registry is **strongly encouraged**.

Run the following to build the Cnocourse Pipeline.yml files:

```sh
CODE_VERSION=main npm run build
```

Upload the `corgi-local.yml` (and `webhost-local.yml` if you want) instructions are in the next section.


## Option B: Build an image and upload to local Docker Registry

```sh
cd ../ # main repo directory

# Build the Docker image and upload it to local registry
# Note: Use 'main' because the RANDOM_DEV_CODEVERSION_PREFIX related code assumes this tag name
export TAG='localhost:5000/openstax/richb-press:main' && docker build --tag $TAG . && docker push $TAG

# Verify the image is in the registry:
# http://localhost:5000/v2/_catalog
# http://localhost:5000/v2/openstax/richb-press/tags/list    : verify that "main" exists

# Build the concourse pipeline to point to our local registry
cd ./build-concourse/
DOCKER_REPOSITORY='openstax/richb-press' DOCKER_REGISTRY_HOST='registry:5000' CODE_VERSION='main' npm run build

# Send the pipeline definition to concourse (next section)
```

# Upload pipeline to concourse

Once the .yml file is created, upload it to concourse by running the following:

```sh
~/Downloads/fly --target local set-pipeline --pipeline corgi --config ./corgi-local.yml
```


# Mock CORGI API

To trigger the CORGI pipeline you will need to mock the CORGI API. docker-compose has already started a mock webserver (smocker) that you just need to upload the CORGI JSON responses to.

Once you upload the the mock you can wait a minute for concourse to poll and find it our you can refresh the resource directly by clicking it in http://localhost:8080/teams/main/pipelines/corgi

Ensure that CORGI_API_URL in [env/corgi-local.json](./env/corgi-local.json) points to `http://smocker:8080/api`

The following snippet starts up one of each type of CORGI job but you can tweak it.
Upload the following (tweak it to change which jobs are pulled) by visiting http://localhost:8081/pages/mocks

```yaml
# See https://github.com/openstax/output-producer-resource/blob/master/src/in_.py for the consumer of this API
# JobType.ARCHIVE_PDF = 1
# JobType.ARCHIVE_DIST_PREVIEW = 2
# JobType.GIT_PDF = 3
# JobType.GIT_DIST_PREVIEW = 4
- request:
    method: GET
    path: /api/jobs
  response:
    headers:
      Content-Type: application/json
    body: >
        [{
            "job_type_id": "3",
            "id": "3333",
            "status_id": "1"
        },
        {
            "job_type_id": "4",
            "id": "4444",
            "status_id": "1"
        },
        {
            "job_type_id": "1",
            "id": "1111",
            "status_id": "1"
        },
        {
            "job_type_id": "2",
            "id": "2222",
            "status_id": "1"
        }]

- request:
    method: GET
    path: /api/jobs/1111
  response:
    headers:
      Content-Type: application/json
    body: >
        {
            "collection_id": "col11992",
            "version": null,
            "style": "astronomy",
            "content_server": {
                "hostname": "cnx.org",
                "host_url": "https://cnx.org",
                "name": "production",
                "id": "11"
            }
        }
- request:
    method: GET
    path: /api/jobs/2222
  response:
    headers:
      Content-Type: application/json
    body: >
        {
            "collection_id": "col11992",
            "version": null,
            "style": "astronomy",
            "content_server": {
                "hostname": "cnx.org",
                "host_url": "https://cnx.org",
                "name": "production",
                "id": "11"
            }
        }
- request:
    method: GET
    path: /api/jobs/3333
  response:
    headers:
      Content-Type: application/json
    body: >
        {
            "collection_id": "philschatz/tiny-book/book-slug1",
            "version": null,
            "style": "astronomy",
            "content_server": null
        }
- request:
    method: GET
    path: /api/jobs/4444
  response:
    headers:
      Content-Type: application/json
    body: >
        {
            "collection_id": "philschatz/tiny-book/book-slug1",
            "version": null,
            "style": "astronomy",
            "content_server": null
        }

- request:
    method: PUT
    path: /api/jobs/1111
  response:
    headers:
      Content-Type: application/json
    body: >
        {"id": "1111"}
- request:
    method: PUT
    path: /api/jobs/2222
  response:
    headers:
      Content-Type: application/json
    body: >
        {"id": "2222"}
- request:
    method: PUT
    path: /api/jobs/3333
  response:
    headers:
      Content-Type: application/json
    body: >
        {"id": "3333"}
- request:
    method: PUT
    path: /api/jobs/4444
  response:
    headers:
      Content-Type: application/json
    body: >
        {"id": "4444"}
```


# Linux-specific Notes

If you are testing a legacy archive job (rather than a git job) then be sure to set the BAGGAGECLAIM_DRIVER to naive in the docker-compose.yml file when starting up concourse. The archive job reuses the same directory for different tasks.

```
CONCOURSE_WORKER_BAGGAGECLAIM_DRIVER: naive
```


# Debugging

## `resource type 'output-producer' has no version`

This usually means the resource is not in the registry. Verify that the resource definition in the pipeline.yml file is correct. If you are using a local registry, you can use these API links to see which images are in the local registry:

- http://localhost:5000/v2/_catalog
- http://localhost:5000/v2/openstax/richb-press/tags/list    : verify that "main" exists

## `failed to create volume`

If you are running an archive job on Linux try setting `CONCOURSE_WORKER_BAGGAGECLAIM_DRIVER: naive` in docker-compose.yml. The archive jobs read/write to the same directories and the this method (which just copies everything between tasks) seems to work.

Also, if you are running out of disk space consider running `docker volume prune` to remove any dangling volumes.