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
export TAG='localhost:5000/book-pipeline:main'
docker build --tag $TAG .
docker push $TAG

# Build the concourse pipeline to point to
cd ./build-concourse/
DOCKER_REPOSITORY='book-pipeline' DOCKER_REGISTRY_HOST='registry:5000' CODE_VERSION='main' npm start

# Send to concourse:
# ~/Downloads/fly --target local set-pipeline --pipeline corgi --config ./corgi-local.yml
```

