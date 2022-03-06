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
    task: 'patch-same-book-links book',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: 'disassembled-book' }
      ],
      outputs: [
        { name: 'disassembled-linked-book' },
        { name: 'common-log' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          cp -r disassembled-book/* disassembled-linked-book
          collection_id="$(cat book/collection_id)"
          book_dir="disassembled-linked-book/$collection_id/disassembled"
          target_dir="disassembled-linked-book/$collection_id/disassembled-linked"
          mkdir "$target_dir"
          patch-same-book-links "$book_dir" "$target_dir" "collection"
          cp "$book_dir"/*@*-metadata.json "$target_dir"
          cp "$book_dir"/collection.toc* "$target_dir"
        `
        ]
      }
    }
  }
}

module.exports = task
