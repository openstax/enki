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

# Creating a new Web-Hosting pipeline in Concourse

If you have a code version, you know how to use fly, and you want to create a new web-hosting pipeline, then this is what you want to read.

You can create a web-hosting pipeline manually or you can use the set-webhosting script.

## Manually Create a Web-Hosting Pipeline

1. In your terminal, go to [enki/build-concourse](./)
1. Run npm install
1. Run `CODE_VERSION='<your-code-version>' npm run build:webhosting`
1. Check https://hub.docker.com/r/openstax/enki/tags to ensure the new code version matches a tag.
1. Login with `fly -t v7 login` (your target might be different, mine is called v7. You can use `fly targets` to list your targets. It's url will be something like ....openstax.org)
1. Run `fly -t v7 sp -p webhost-prod-<your-code-version> -c ./webhosting-production.yml`

## Using the set-webhosting Script

To run the set-webhosting script, you will need node version >= 18. This script uses the **experimental** fetch api introduced in node version 18. This api is supposed to be [stable as of node version 21](https://devclass.com/2023/10/17/node-js-21-released-with-stable-fetch-api-node-js-20-becomes-long-term-support-release/).

This script automatically does every step you would do manually. Run it like this:
1. In your terminal, go to [enki/build-concourse](./)
1. Run npm install
1. Run `CODE_VERSION='<your-code-version>' npm run set:webhosting`

You may need to login with fly, but it should prompt you for that.

This script searches your ~/.flyrc for a target with a url ending in `.openstax.org`. If you do not have a target with this url yet, you can configure it with `fly -t <target-name> -c <url>`

# Install Prerequisites

1. Start up concourse and the Docker registry by running `docker-compose up -d` in this directory (See **Linux Notes** below)
1. Sign in to concourse by visiting http://localhost:8080 and using `test` and `test` for the username/password
1. Download the fly command (into `~/Downloads/fly`)
1. Make it executable by running `chmod 755 ~/Downloads/fly`
1. Authenticate through the commandline by running `~/Downloads/fly --target local login --concourse-url http://localhost:8080` and opening the link that it prints out

Now you can build a pipeline using `npm run build:local` and upload it to concourse.


# Pipeline.yml Build Alternatives

If you are changing code inside the docker image you will need to upload the image to a local registry (see **Option B**). If you are not editing code inside the image then you can use the [main tag on dockerhub](https://hub.docker.com/r/openstax/enki/tags) by following the instructions in **Option A**.

In both cases you will want to set the AWS credentials which will be used to upload to S3 (e.g. `source /path/to/set_aws_creds -r sandbox:full-admin -t ######`).

If you are not testing the upload parts you can provide dummy values for the following:

- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY


## Option A: Use image on DockerHub

Since we are not changing the image we can use the images on dockerhub.
DockerHub does have a rate limit. If you start too many jobs, Concourse will provide a cryptic error.

At that point you can switch to **Option B** (a local registry is **strongly encouraged**).

Run the following to build the Cnocourse Pipeline.yml files:

```sh
CODE_VERSION=main npm run build:local
```

Upload the `corgi-local.yml` (and `webhost-local.yml` if you want) instructions are in the next section.


## Option B: Build an image and upload to local Docker Registry

```sh
cd ../ # main repo directory

# Build the Docker image and upload it to local registry
# Note: Use 'main' because the RANDOM_DEV_CODEVERSION_PREFIX related code assumes this tag name
export DOCKER_BUILDKIT=1 TAG='localhost:5000/openstax/enki:main' && docker build --tag $TAG . && docker push $TAG

# Verify the image is in the registry:
# http://localhost:5000/v2/_catalog
# http://localhost:5000/v2/openstax/enki/tags/list    : verify that "main" exists

# Build the concourse pipeline to point to our local registry
cd ./build-concourse/
DOCKER_REPOSITORY='openstax/enki' DOCKER_REGISTRY_HOST='registry:5000' CODE_VERSION='main' npm run build:local

# Send the pipeline definition to concourse (next section)
```

# Upload pipeline to concourse

Once the .yml file is created, upload it to concourse by running the following:

```sh
~/Downloads/fly --target local set-pipeline --pipeline corgi --config ./corgi-local.yml
```


# Mock CORGI API

To trigger the CORGI pipeline you will need to mock the CORGI API. docker-compose has already started a mock webserver (smocker) that you just need to upload the CORGI JSON responses to.

Once you upload the mock you can wait a minute for concourse to poll and find it our you can refresh the resource directly by clicking it in http://localhost:8080/teams/main/pipelines/corgi

Ensure that CORGI_API_URL in [env/corgi-local.json](./env/corgi-local.json) points to `http://smocker:8080/api`

The following snippet starts up one of each type of CORGI job but you can tweak it.
Upload the following (tweak it to change which jobs are pulled) by visiting http://localhost:8081/pages/mocks

```yaml
# See https://github.com/openstax/enki/blob/main/corgi-concourse-resource/src/in_.py for the consumer of this API
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
        }]

- request:
    method: GET
    path: /api/jobs/3333
  response:
    headers:
      Content-Type: application/json
    body: >
      {
        "status_id": "1",
        "job_type_id": "3",
        "version": "18ca7dfc49392e2cb93352c528a140e7d02a030c",
        "worker_version": "1",
        "id": "3333",
        "created_at": "2022-10-24T22:44:09.845510",
        "updated_at": "2022-10-24T22:44:09.845515",
        "status": {
          "name": "assigned",
          "id": "2"
        },
        "repository": {
          "name": "osbooks-college-success",
          "owner": "openstax"
        },
        "job_type": {
          "name": "git-web-hosting-preview",
          "display_name": "Web Preview (git)",
          "id": "4"
        },
        "user": {
          "name": "Staxly",
          "avatar_url": "https://avatars.githubusercontent.com/u/10718832?v=4",
          "id": "10718832"
        },
        "books": [
          {
            "slug": "college-success",
            "commit_id": "1",
            "edition": 0,
            "style": "college-success",
            "uuid": "e8668a14-9a7d-4d74-b58c-3681f8351224"
          }
        ],
        "artifact_urls": [
          {
            "slug": "college-success",
            "url": null
          }
        ]
      }
- request:
    method: GET
    path: /api/jobs/4444
  response:
    headers:
      Content-Type: application/json
    body: >
      {
        "status_id": "1",
        "job_type_id": "4",
        "version": "18ca7dfc49392e2cb93352c528a140e7d02a030c",
        "worker_version": "1",
        "id": "4444",
        "created_at": "2022-10-24T22:44:09.845510",
        "updated_at": "2022-10-24T22:44:09.845515",
        "status": {
          "name": "assigned",
          "id": "2"
        },
        "repository": {
          "name": "osbooks-college-success",
          "owner": "openstax"
        },
        "job_type": {
          "name": "git-web-hosting-preview",
          "display_name": "Web Preview (git)",
          "id": "4"
        },
        "user": {
          "name": "Staxly",
          "avatar_url": "https://avatars.githubusercontent.com/u/10718832?v=4",
          "id": "10718832"
        },
        "books": [
          {
            "slug": "college-success",
            "commit_id": "1",
            "edition": 0,
            "style": "college-success",
            "uuid": "e8668a14-9a7d-4d74-b58c-3681f8351224"
          }
        ],
        "artifact_urls": [
          {
            "slug": "college-success",
            "url": null
          }
        ]
      }

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


# Debugging

## `resource type 'corgi-resource' has no version`

This usually means the resource is not in the registry. Verify that the resource definition in the pipeline.yml file is correct. If you are using a local registry, you can use these API links to see which images are in the local registry:

- http://localhost:5000/v2/_catalog
- http://localhost:5000/v2/openstax/enki/tags/list    : verify that "main" exists

## `check did not return a version`

Same error as above. The registry might have _a_ tag of the repo but not _the_ tag  that is specified in the pipeline.yml file. Use the URLs above to see which tags are available

## `failed to create volume`

If you are running an archive job on Linux try setting `CONCOURSE_WORKER_BAGGAGECLAIM_DRIVER: naive` in docker-compose.yml. The archive jobs read/write to the same directories and the this method (which just copies everything between tasks) seems to work.

Also, if you are running out of disk space consider running `docker volume prune` to remove any dangling volumes.

## `failed to fetch image`

If you are getting this error, it might help if you modify `corgi-local.yml` to use your host machine's IP address instead of `registry` and `smocker` (i.e. `registry:5000/openstax/enki` -> `x.x.x.x:5000/openstax/enki`). 

If you are still having problems, here are some additional things to try
  - Try adding `CONCOURSE_WORKER_RUNTIME: "containerd"`
  - If that does not help, download the [official concourse docker-compose.yml](https://concourse-ci.org/docker-compose.yml) file and add registry/smocker to it and use that instead of the one in this directory
  - If that does not help, check to make sure that your concourse instance is utilizing its volumes. If all of it's volumes are at 0 bytes even after you `docker-compose down` it, you should consider trying a different version of concourse.