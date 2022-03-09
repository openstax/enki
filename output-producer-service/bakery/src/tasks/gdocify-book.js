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
    task: 'gdocify book',
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
      outputs: [{ name: 'gdocified-book' }],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          dedent`
          exec 2> >(tee gdocified-book/stderr >&2)
          cp -r disassembled-book/* gdocified-book
          collection_id="$(cat book/collection_id)"
          book_dir="gdocified-book/$collection_id/disassembled"
          target_dir="gdocified-book/$collection_id/gdocified"
          book_slugs_file="/tmp/book-slugs.json"
          cat "gdocified-book/$collection_id/approved-book-list.json" | jq ".approved_books|map(.books)|flatten" > "$book_slugs_file"
          mkdir "$target_dir"
          curl -o /tmp/AdobeICCProfiles.zip https://download.adobe.com/pub/adobe/iccprofiles/win/AdobeICCProfilesCS4Win_end-user.zip
          unzip -o -j "/tmp/AdobeICCProfiles.zip" "Adobe ICC Profiles (end-user)/CMYK/USWebCoatedSWOP.icc" -d /usr/share/color/icc/
          rm -f /tmp/AdobeICCProfiles.zip
          gdocify "$book_dir" "$target_dir" "$book_slugs_file"
          cp "$book_dir"/*@*-metadata.json "$target_dir"
        `
        ]
      }
    }
  }
}

module.exports = task
