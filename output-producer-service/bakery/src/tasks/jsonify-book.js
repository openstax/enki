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
    task: 'jsonify book',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: 'disassembled-linked-book' }
      ],
      outputs: [
        { name: 'jsonified-book' },
        { name: 'common-log' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          cp -r disassembled-linked-book/* jsonified-book
          collection_id="$(cat book/collection_id)"
          book_dir="jsonified-book/$collection_id/disassembled-linked"
          target_dir="jsonified-book/$collection_id/jsonified"
          mkdir "$target_dir"
          jsonify "$book_dir" "$target_dir"
          jsonschema -i "$target_dir/collection.toc.json" /code/scripts/book-schema.json
          for jsonfile in "$target_dir/"*@*.json; do
            jsonschema -i "$jsonfile" /code/scripts/page-schema.json
          done
        `
        ]
      }
    }
  }
}

module.exports = task
