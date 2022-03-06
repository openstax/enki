const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const { codeVersion, cloudfrontUrl, distBucketPath, jsonifiedInput, contentSource: maybeContentSource } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  const contentSource = maybeContentSource != null ? maybeContentSource : 'archive'

  const distBucketPrefix = `${distBucketPath}${codeVersion}`

  const rexUrl = 'https://rex-web.herokuapp.com'
  const rexProdUrl = 'https://rex-web-production.herokuapp.com'

  return {
    task: 'generate preview urls',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: `${jsonifiedInput}` }
      ],
      outputs: [
        { name: 'preview-urls' },
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
              book_dir="${jsonifiedInput}/$collection_id/jsonified"
              book_metadata="$book_dir/collection.toc.json"
              ;;
            git)
              book_slug="$(cat book/slug)"
              book_metadata="${jsonifiedInput}/$book_slug.toc.json"
              ;;
            *)
              echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
              exit 1
              ;;
          esac

          book_uuid=$(jq -r '.id' "$book_metadata")
          book_version=$(jq -r '.version' "$book_metadata")

          rex_archive_param="?archive=${cloudfrontUrl}/${distBucketPrefix}"

          first_page_slug=$(jq -r '.tree.contents[0].slug' "$book_metadata")
          rex_url="${rexUrl}/books/$book_uuid@$book_version/pages/$first_page_slug$rex_archive_param"
          rex_prod_url="${rexProdUrl}/books/$book_uuid@$book_version/pages/$first_page_slug$rex_archive_param"

          jq \
            --arg rex_url $rex_url \
            --arg rex_prod_url $rex_prod_url \
            '. + [
              { text: "View - Rex Web", href: $rex_url },
              { text: "View - Rex Web Prod", href: $rex_prod_url }
            ]' \
            <<< '[]' >> preview-urls/content_urls
        `
        ]
      }
    }
  }
}

module.exports = task
