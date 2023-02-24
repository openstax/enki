# Design

There are several goals for this little project:

- manipulate XML easily by making it easy to select and create elements
- rename/move a file and have all the references to it be written correctly

And some minor features:

- preserve sourcemaps when we move content
- include sourcemaps when we create elements

# Run Locally

```
./bin/epub ../data/astronomy/_attic ./testing
```

# Tests

```sh
npm install
npm test
```
