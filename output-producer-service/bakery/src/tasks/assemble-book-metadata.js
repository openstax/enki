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
    task: 'assemble book metadata',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: 'assembled-book' }
      ],
      outputs: [
        { name: 'assembled-book-metadata' },
        { name: 'common-log' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          collection_id="$(cat book/collection_id)"
          book_dir="assembled-book/$collection_id"
          target_dir="assembled-book-metadata/$collection_id"
          mkdir "$target_dir"

          echo "{" > uuid-to-revised-map.json
          find assembled-book/$collection_id/raw/ -path */m*/metadata.json | xargs cat | jq -r '. | "\"\(.id)\": \"\(.revised)\","' >> uuid-to-revised-map.json
          echo '"dummy": "dummy"' >> uuid-to-revised-map.json
          echo "}" >> uuid-to-revised-map.json

          assemble-meta "$book_dir/collection.assembled.xhtml" uuid-to-revised-map.json "$target_dir/collection.assembled-metadata.json"
        `
        ]
      }
    }
  }
}

module.exports = task
