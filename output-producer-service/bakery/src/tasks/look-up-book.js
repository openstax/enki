const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const imageDefault = {
    name: 'openstax/nebuchadnezzar',
    tag: 'trunk'
  }
  const { inputSource, image, contentSource: maybeContentSource } = taskArgs
  const imageOverrides = image != null ? image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  const contentSource = maybeContentSource != null ? maybeContentSource : 'archive'

  return {
    task: 'look up book',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [{ name: inputSource }],
      outputs: [
        { name: 'book' },
        { name: 'common-log' }
      ],
      params: {
        CONTENT_SOURCE: contentSource
      },
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          tail ${inputSource}/*
          cp ${inputSource}/id book/job_id
          cp ${inputSource}/version book/version
          cp ${inputSource}/collection_style book/style
          case $CONTENT_SOURCE in
            archive)
              cp ${inputSource}/collection_id book/collection_id
              cp ${inputSource}/content_server book/server
              wget -q -O jq 'https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64' && chmod +x jq
              server_shortname="$(cat ${inputSource}/job.json | ./jq -r '.content_server.name')"
              echo "$server_shortname" >book/server_shortname
              pdf_filename="$(cat book/collection_id)-$(cat book/version)-$(cat book/server_shortname)-$(cat book/job_id).pdf"
              echo "$pdf_filename" > book/pdf_filename
              ;;
            git)
              cat ${inputSource}/collection_id | awk -F'/' '{ print $1 }' > book/repo
              cat ${inputSource}/collection_id | awk -F'/' '{ print $2 }' | sed 's/ *$//' > book/slug
              pdf_filename="$(cat book/slug)-$(cat book/version)-git-$(cat book/job_id).pdf"
              echo "$pdf_filename" > book/pdf_filename
              ;;
            *)
              echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
              exit 1
              ;;
          esac
        `
        ]
      }
    }
  }
}

module.exports = task
