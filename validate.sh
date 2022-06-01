#!/bin/bash

src_dir=~/.local/share/enki-data/_attic/IO_EPUB
epub_file=~/Downloads/test.epub
validator_jar=~/Downloads/epubcheck-4.2.2/epubcheck.jar

[[ -f $epub_file ]] && rm $epub_file

pushd $src_dir
zip -q -X -r $epub_file ./mimetype ./META-INF ./contents ./resources
popd

java -jar $validator_jar --error $epub_file