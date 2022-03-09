const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const { awsAccessKeyId, awsSecretAccessKey, distBucket, codeVersion, distBucketPath } = taskArgs
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })
  if (!distBucketPath.endsWith('/') || distBucketPath.length === 0) {
    throw Error('distBucketPath must represent some directory-like path in s3')
  }
  const distBucketPrefix = `${distBucketPath}${codeVersion}`

  return {
    task: 'upload book',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      params: {
        AWS_ACCESS_KEY_ID: `${awsAccessKeyId}`,
        AWS_SECRET_ACCESS_KEY: `${awsSecretAccessKey}`
      },
      inputs: [
        { name: 'book' },
        { name: 'jsonified-book' }
      ],
      outputs: [
        { name: 'common-log' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          collection_id="$(cat book/collection_id)"
          book_dir="jsonified-book/$collection_id/jsonified"
          book_metadata="jsonified-book/$collection_id/raw/metadata.json"
          resources_dir="jsonified-book/$collection_id/resources"
          target_dir="upload-book/contents"
          mkdir -p "$target_dir"
          book_uuid="$(cat $book_metadata | jq -r '.id')"
          book_version="$(cat $book_metadata | jq -r '.version')"
          for jsonfile in "$book_dir/"*@*.json; do cp "$jsonfile" "$target_dir/$(basename $jsonfile)"; done;
          for xhtmlfile in "$book_dir/"*@*.xhtml; do cp "$xhtmlfile" "$target_dir/$(basename $xhtmlfile)"; done;
          aws s3 cp --recursive "$target_dir" "s3://${distBucket}/${distBucketPrefix}/contents"
          copy-resources-s3 "$resources_dir" "${distBucket}" "${distBucketPrefix}/resources"

          #######################################
          # UPLOAD BOOK LEVEL FILES LAST
          # so that if an error is encountered
          # on prior upload steps, those files
          # will not be found by watchers
          #######################################
          toc_s3_link_json="s3://${distBucket}/${distBucketPrefix}/contents/$book_uuid@$book_version.json"
          toc_s3_link_xhtml="s3://${distBucket}/${distBucketPrefix}/contents/$book_uuid@$book_version.xhtml"
          aws s3 cp "$book_dir/collection.toc.json" "$toc_s3_link_json"
          aws s3 cp "$book_dir/collection.toc.xhtml" "$toc_s3_link_xhtml"
        `
        ]
      }
    }
  }
}

module.exports = task
