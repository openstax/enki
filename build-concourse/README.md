To deploy the pipeline to a local concourse:

```sh
# Use set_aws_creds to obtain a token
source /path/to/set_aws_creds -r sandbox:full-admin -t ######

npm start; /path/to/concourse-command/fly --target local set-pipeline --pipeline webhost-pipeline --config ./build-web.yml

```

# Use a local docker registry isntead of DockerHub

```sh
cd ../ # main repo directory

# Build the Docker image and upload it to local registry
# Note: Use 'main' because the RANDOM_DEV_CODEVERSION_PREFIX related code assumes this tag name
export TAG='localhost:5000/openstax/book-pipeline:main' && docker build --tag $TAG . && docker push $TAG

# Swith to the output-producer-resource repository
export TAG='localhost:5000/openstax/output-producer:latest' && docker build --tag $TAG . && docker push $TAG

# Verify the images are in the registry:
# http://localhost:5000/v2/_catalog
# http://localhost:5000/v2/openstax/book-pipeline/tags/list

# Build the concourse pipeline to point to
cd ./build-concourse/
DOCKER_REPOSITORY='openstax/book-pipeline' DOCKER_REGISTRY_HOST='registry:5000' CODE_VERSION='main' npm start


# Send to concourse:
# ~/Downloads/fly --target local set-pipeline --pipeline corgi --config ./corgi-local.yml
```

# Using the builtin mock server

change the CORGI_API_URL in [env/corgi-local.json](./env/corgi-local.json) to point to `http://smocker:8080/api`

Upload the following (tweak it to change which job is pulled) to http://localhost:8081/pages/mocks

```yaml
- request:
    method: PUT
    path: /api/jobs/123
  response:
    headers:
      Content-Type: application/json
    body: >
        {"id": "123"}

- request:
    method: GET
    path: /api/jobs/123
  response:
    headers:
      Content-Type: application/json
    body: >
        {
            "collection_id": "col11992",
            "status_id": "1",
            "pdf_url": null,
            "worker_version": null,
            "error_message": null,
            "content_server_id": "11",
            "version": null,
            "style": "astronomy",
            "job_type_id": "1",
            "id": "123",
            "created_at": "2021-05-25T14:29:32.675108",
            "updated_at": "2021-05-25T14:30:28.118520",
            "status": {
                "name": "processing",
                "id": "2"
            },
            "content_server": {
                "hostname": "cnx.org",
                "host_url": "https://cnx.org",
                "name": "production",
                "id": "11"
            },
            "job_type": {
                "name": "pdf",
                "display_name": "PDF",
                "id": "1"
            }
        }

- request:
    method: GET
    path: /api/jobs
  response:
    headers:
      Content-Type: application/json
    body: >
        [{
            "status_id": "1",
            "job_type_id": "1",
            "id": "123"
        }]
```

Use the following cheat-sheet for job types:

```typescript
export enum JobType {
    ARCHIVE_PDF = 1,
    ARCHIVE_DIST_PREVIEW = 2,
    GIT_PDF = 3,
    GIT_DIST_PREVIEW = 4
}
export enum Status {
    QUEUED = 1,
    ASSIGNED = 2,
    PROCESSING = 3,
    FAILED = 4,
    SUCCEEDED = 5,
    ABORTED = 6
}
```
