# Instructions

```sh
# Create the image by building all the repos
docker build -t my_image .

# Fetch a book and put it in the ./data/physics/ directory
COL_ID=col12006 BOOK=physics   docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image fetch ${COL_ID}
COL_ID=col11407 BOOK=sociology docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image fetch ${COL_ID}

# Assemble a book
BOOK=physics   docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image assemble
BOOK=sociology docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image assemble

# Link Extras
BOOK=physics   docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image link-extras
BOOK=sociology docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image link-extras

# Bake a book
RECIPE=college-physics BOOK=physics   docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image bake ${RECIPE}
RECIPE=sociology       BOOK=sociology docker run -it -v $(pwd)/data/${BOOK}/:/data/ --rm my_image bake ${RECIPE}

# Mathify a book


# PDF a book
```