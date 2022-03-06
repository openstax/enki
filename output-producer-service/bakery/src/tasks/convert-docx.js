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
    task: 'convert to docx',
    config: {
      platform: 'linux',
      image_resource: {
        type: 'docker-image',
        source: imageSource
      },
      inputs: [
        { name: 'book' },
        { name: 'gdocified-book' }
      ],
      outputs: [{ name: 'docx-book' }],
      run: {
        path: '/bin/bash',
        args: [
          '-cxe',
          /* eslint-disable no-template-curly-in-string */
          dedent`
          exec 2> >(tee docx-book/stderr >&2)
          pushd /code/scripts
          pm2 start mml2svg2png-json-rpc.js --node-args="-r esm" --wait-ready --listen-timeout 8000
          popd
          cp -r gdocified-book/* docx-book
          collection_id="$(cat book/collection_id)"
          book_dir="docx-book/$collection_id/gdocified"
          target_dir="docx-book/$collection_id/docx"
          mkdir "$target_dir"
          cd "$book_dir"
          for xhtmlfile in ./*@*.xhtml; do
            xhtmlfile_basename=$(basename "$xhtmlfile")
            metadata_filename="${'${xhtmlfile_basename%.*}'}"-metadata.json
            docx_filename=$(cat "$metadata_filename" | jq -r '.slug').docx
            mathmltable_tempfile="${'${xhtmlfile}'}.mathmltable.tmp"
            mathmltable2png "$xhtmlfile" "../resources" "$mathmltable_tempfile"
            wrapped_tempfile="${'${xhtmlfile}'}.greybox.tmp"
            xsltproc --output "$wrapped_tempfile" /code/gdoc/wrap-in-greybox.xsl "$mathmltable_tempfile"
            pandoc --reference-doc="/code/gdoc/custom-reference.docx" --from=html --to=docx --output="../../../$target_dir/$docx_filename" "$wrapped_tempfile"
          done
          pm2 stop mml2svg2png-json-rpc
        `
        /* eslint-enable no-template-curly-in-string */
        ]
      }
    }
  }
}

module.exports = task
