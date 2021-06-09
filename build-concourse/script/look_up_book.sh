exec > >(tee $IO_COMMON_LOG/log >&2) 2>&1

tail $INPUT_SOURCE_DIR/*
cp $INPUT_SOURCE_DIR/id $IO_BOOK/job_id
cp $INPUT_SOURCE_DIR/version $IO_BOOK/version
cp $INPUT_SOURCE_DIR/collection_style $IO_BOOK/style
case $CONTENT_SOURCE in
    archive)
        cp $INPUT_SOURCE_DIR/collection_id $IO_BOOK/collection_id
        cp $INPUT_SOURCE_DIR/content_server $IO_BOOK/server
        wget -q -O jq 'https://github.com/stedolan/jq/releases/download/jq-1.6/jq-linux64' && chmod +x jq
        server_shortname="$(cat $INPUT_SOURCE_DIR/job.json | ./jq -r '.content_server.name')"
        echo "$server_shortname" >$IO_BOOK/server_shortname
        pdf_filename="$(cat $IO_BOOK/collection_id)-$(cat $IO_BOOK/version)-$(cat $IO_BOOK/server_shortname)-$(cat $IO_BOOK/job_id).pdf"
        echo "$pdf_filename" > $IO_BOOK/pdf_filename
        ;;
    git)
        if [[ $(cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $3 }') ]]; then
            cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $1 "/" $2 }' > $IO_BOOK/repo
            cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $3 }' | sed 's/ *$//' > $IO_BOOK/slug
        else
            cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $1 }' > $IO_BOOK/repo
            cat $INPUT_SOURCE_DIR/collection_id | awk -F'/' '{ print $2 }' | sed 's/ *$//' > $IO_BOOK/slug
        fi
        pdf_filename="$(cat $IO_BOOK/slug)-$(cat $IO_BOOK/version)-git-$(cat $IO_BOOK/job_id).pdf"
        echo "$pdf_filename" > $IO_BOOK/pdf_filename
        ;;
    *)
        echo "CONTENT_SOURCE unrecognized: $CONTENT_SOURCE"
        exit 1
        ;;
esac