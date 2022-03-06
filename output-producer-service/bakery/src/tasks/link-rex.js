const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const { inputSource, contentSource: maybeContentSource } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  const contentSource = maybeContentSource != null ? maybeContentSource : 'archive'

  return {
    task: 'link rex',
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
        { name: 'rex-linked' },
        { name: 'common-log' }
      ],
      params: {
        CONTENT_SOURCE: `${contentSource}`
      },
      run: {
        user: 'root',
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1
          case $CONTENT_SOURCE in
            archive)
              cp -r "${inputSource}"/* rex-linked
              collection_id="$(cat book/collection_id)"
              book_dir="${inputSource}/$collection_id"
              xhtmlfiles_path="$book_dir/collection.mathified.xhtml"
              abl_file="$book_dir/approved-book-list.json"
              target_dir="rex-linked/$collection_id/"
              filename="collection.rex-linked.xhtml"
              book_slugs_file="/tmp/book-slugs.json"
              cat $abl_file | jq ".approved_books|map(.books)|flatten" > "$book_slugs_file"
              ;;
            git)
              xhtmlfiles_path="${inputSource}/*.mathified.xhtml"
              target_dir="rex-linked"
              filename="$(cat book/slug).rex-linked.xhtml"
              book_slugs_file="idontexistforGit"
              ;;
            *)
              echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
              exit 1
              ;;
          esac

          for xhtmlfile in $xhtmlfiles_path
          do
            link-rex "$xhtmlfile" "$book_slugs_file" "$target_dir" "$filename"
          done
        `
        ]
      }
    }
  }
}

module.exports = task
