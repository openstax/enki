const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const { inputSource, inputPath, validationNames, contentSource: maybeContentSource } = taskArgs
  const imageDefault = {
    name: 'openstax/xhtml-validator',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  const contentSource = maybeContentSource != null ? maybeContentSource : 'archive'

  return {
    task: 'validate xhtml',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: `${inputSource}` }
      ],
      outputs: [
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

          case $CONTENT_SOURCE in
            archive)
              collection_id="$(cat book/collection_id)"
              xhtmlfiles_path="${inputSource}/$collection_id/"${inputPath}
              ;;
            git)
              xhtmlfiles_path="${inputSource}/"${inputPath}
              ;;
            *)
              echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
              exit 1
              ;;
          esac
          failure=false
          for xhtmlfile in $xhtmlfiles_path
          do
            java -cp /xhtml-validator.jar org.openstax.xml.Main - ${validationNames.join(' ')} < "$xhtmlfile" || failure=true
          done
          if $failure; then
            exit 1
          fi
        `
        ]
      }
    }
  }
}

module.exports = task
