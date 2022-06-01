src_dir=$IO_EPUB
epub_file=/tmp/test.epub
validator_jar=$PROJECT_ROOT/epub-validator/epubcheck-$EPUB_VALIDATOR_VERSION/epubcheck.jar

[[ -f $epub_file ]] && rm $epub_file

pushd $src_dir
zip -q -X -r $epub_file ./mimetype ./META-INF ./contents ./resources
popd

java -jar $validator_jar --error $epub_file