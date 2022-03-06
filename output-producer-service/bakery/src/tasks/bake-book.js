const dedent = require('dedent')

const { constructImageSource } = require('../task-util/task-util')

const task = (taskArgs) => {
  const imageDefault = {
    name: 'openstax/recipes',
    tag: 'trunk'
  }
  const imageOverrides = taskArgs != null && taskArgs.image != null ? taskArgs.image : {}
  const imageSource = constructImageSource({ ...imageDefault, ...imageOverrides })

  return {
    task: 'bake book',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: 'linked-extras' },
        { name: 'cnx-recipes-output' }
      ],
      outputs: [
        { name: 'baked-book' },
        { name: 'common-log' }
      ],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec > >(tee common-log/log >&2) 2>&1

          cp -r linked-extras/* baked-book
          book_dir="baked-book/$(cat book/collection_id)"
          /code/bake_root -b "$(cat book/style)" -r cnx-recipes-output/rootfs/recipes -i "$book_dir/collection.linked.xhtml" -o "$book_dir/collection.baked.xhtml"
          style_file="cnx-recipes-output/rootfs/styles/$(cat book/style)-pdf.css"
          if [ -f "$style_file" ]
          then
            cp "$style_file" $book_dir
            sed -i "s%<\\/head>%<link rel=\"stylesheet\" type=\"text/css\" href=\"$(basename $style_file)\" />&%" "$book_dir/collection.baked.xhtml"
          else
            echo "Warning: Style Not Found" >baked-book/stderr
          fi
        `
        ]
      }
    }
  }
}

module.exports = task
