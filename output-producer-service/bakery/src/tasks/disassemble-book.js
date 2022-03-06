const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const imageDefault = {
    name: 'openstax/cops-bakery-scripts',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  return {
    task: 'disassemble book',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: 'fetched-book' },
        { name: 'checksum-book' },
        { name: 'baked-book-metadata' }
      ],
      outputs: [
        { name: 'disassembled-book' },
        { name: 'common-log' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          collection_id="$(cat book/collection_id)"
          book_metadata="fetched-book/$collection_id/raw/metadata.json"
          book_uuid="$(cat $book_metadata | jq -r '.id')"
          book_version="$(cat $book_metadata | jq -r '.version')"
          cp -r checksum-book/* disassembled-book
          book_dir="disassembled-book/$collection_id"
          cp "baked-book-metadata/$collection_id/collection.baked-metadata.json" "$book_dir/collection.baked-metadata.json"
          mkdir "$book_dir/disassembled"
          disassemble "$book_dir/collection.baked.xhtml" "$book_dir/collection.baked-metadata.json" "collection" "$book_dir/disassembled"
        `
        ]
      }
    }
  }
}

module.exports = task
