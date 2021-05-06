To deploy the pipeline to a local concourse:

```sh
# Use set_aws_creds to obtain a token
source /path/to/set_aws_creds -r sandbox:full-admin -t ######

npm start; /path/to/concourse-command/fly --target local set-pipeline --pipeline webhost-pipeline --config ./build-web.yml

```