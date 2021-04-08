# Instructions

```sh
# Create the image by building all the repos
docker build -t my_image .

# Fetch a book and put it in the ./data/physics/ directory
COL_ID=col12006 BOOK=physics   docker run -it -v $(pwd)/data/${BOOK}:/data/  --rm my_image fetch ${COL_ID}
COL_ID=col11407 BOOK=sociology docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image fetch ${COL_ID}

# Assemble a book
BOOK=physics   docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image assemble
BOOK=sociology docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image assemble

# Link Extras
# https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/link-extras.js#L40

# Bake a book
# https://github.com/openstax/output-producer-service/blob/master/bakery/src/tasks/bake-book.js#L39

```