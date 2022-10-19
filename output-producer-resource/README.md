# output-producer-resource

## Examples

```yaml
resource_types:
  - name: cops-jobs
    type: docker-image
    source:
      repository: openstax/output-producer-resource

resources:
  - name: cops-jobs-queued
    type: cops-jobs
    source:
      api_root: https://cc1.cnx.org/api
      status_id: 1

  - name: job-update
    type: cops-jobs
    source:
      api_root: https://cc1.cnx.org/api
```

## `get`: Get the latest jobs from service

### Files created

* `id`: The job id
* `collection_id`: The collection id for the job
* `job.json`: All the api data for the job

### Example

```yaml
plan:
  - get: cops-jobs-queued
    trigger: true
    version: every
```

## `put`: Update the job through the web api

* `status_id`: The id of the status to change the job
* `pdf_url`: The url location of the pdf on S3

### Example

```yaml
- put: job-update
  params:
    id: cops-jobs-queued/id
    status_id: "2"
```

## Configure Dev Environment

Change into the output-producer-resource working directory

`cd ./output-producer-resource`

Create a virtualenv:

`python3 -m venv .venv`

Install dependencies:

`pip install .[dev]`

### Run unit tests

`make test`

### Updating VCR cassettes for unit tests

The VCR cassettes used for unit tests are generated using a local COPS environment. In order to create new cassettes (e.g. for API changes, etc.):

1. Setup a local environment using directions [here](https://github.com/openstax/output-producer-service/blob/master/README.md). Make sure it is in a clean, vanilla state (e.g. make sure your COPS UI has no jobs listed).

2. Delete the existing cassettes which you'd like to update

3. Run the utility script to initialize your local COPS environment with jobs (you may need / want to update this script as well depending upon the changes):

```
python tests/cassettes/init_local_cops.py
```

4. Run the tests via `make test` to generate cassette files

5. (If necessary) Update the `job.json` file by running:

```
curl http://localhost/api/jobs/1 -o tests/data/job.json
```

### Build the docker image for development

`make build-image`

### Build the docker image tagged latest

`make tag-latest`

### Release the versioned image to dockerhub

`make release`

### Release the latest image to dockerhub

`make release-latest`
