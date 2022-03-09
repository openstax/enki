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
    task: 'checksum book',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: 'baked-book' }
      ],
      outputs: [
        { name: 'checksum-book' },
        { name: 'common-log' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          collection_id="$(cat book/collection_id)"
          cp -r baked-book/* checksum-book
          book_dir="checksum-book/$collection_id"
          mkdir "$book_dir/baked"
          find "baked-book/$collection_id/" -maxdepth 1 -type f -exec cp {} $book_dir/baked \;
          checksum "$book_dir" "$book_dir"
        `
        ]
      }
    }
  }
}

module.exports = task
