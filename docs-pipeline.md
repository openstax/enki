# How content changes in enki

This describes the overall steps that content goes through.
Several of these can be clumped together instead of being separate and would reduce the amount of validation & debugging/testing.

* [Overall Process](#overall-process)
* [What happens in each step](#what-happens-in-each-step)
   * [git-fetch](#git-fetch)
   * [git-fetch-metadata](#git-fetch-metadata)
      * [fetch-update-metadata](#fetch-update-metadata)
      * [fetch-map-resources](#fetch-map-resources)
   * [git-assemble](#git-assemble)
   * [git-bake](#git-bake)
   * [git-bake-meta](#git-bake-meta)
   * [git-link](#git-link)
   * [Output-specific](#output-specific)
* [Required languages](#required-languages)
   * [Validation](#validation)


# Overall Process

Listed here is the pipeline steps grouped together into steps that could be combined.

1. [git-fetch](#git-fetch): Clone URL & checkout commit
1. [git-fetch-metadata](#git-fetch-metadata), [git-assemble](#git-assemble)
    - Replace `<md:metadata>` and move images to `../resources/{sha}`, Convert CNXML to HTML and assemble all the files together
1. [git-bake](#git-bake)
1. [git-bake-meta](#git-bake-meta), [git-link](#git-link)
    - Create a book metadata JSON file with slugs and abstracts, add attributes to links for REX so it knows the canonical book
1. Output-specific steps


# What happens in each step

## git-fetch

This just runs an authenticated `git clone` and checks out the correct branch/commit.

**Validation:**

Use POET CLI to validate the results.


## git-fetch-metadata

3 things happen.

1. Replace `<md:metadata>` in CNXML and collxml files
1. Move images/resources into `../resources/`
1. Copy the web style into the resources directory (for use by REX)

### fetch-update-metadata

- The metadata in every CNXML file is replaced with 2 fields: `revised` and `canonical-book-uuid`
- The metadata in every Collection file is replaced with 2 fields: `revised` and `version`

### fetch-map-resources

1. Move resources into a `/resources/{sha}` format
1. update the CNXML references to these resource files
1. generate neighboring JSON files for AWS to help set the content type when browsers fetch the resource

**Validation:**

The results can be validated like so:

1. Should still validate using POET CLI (maybe a minor tweak is necessary?)
1. Every `<link resource="..."` and `<image src="..."` should begin with `../resources/`
1. Every `<md:metadata>` in the CNXML file and the COLLXML file should contain 2 entries
1. A style file exists in `../resources/` wit hcorresponding sourcemap if it exists


## git-assemble

This step performs several things to convert every collection.xml file into a gigantic `{slug}.collection.xhtml`:

1. Convert every CNXML file to an XHTML file
1. Prefix id attributes and links to those attributes with the module ID so they are unique once they are combined into one XML document
1. Depending on the `<c:link>` type, convert it to `<a href="/contents/{MODULE_ID}">` (other-book link), `<a href="#page_{PAGE_ID}">` (same-book link), or `<a href="#page_{PAGE_ID}_{TARGET_ID}">` (element on a page), or `<a href="https://cnx.org/content/{PAGE_ID}">` if the page does not exist in the REPO
    - Also add `class="autogenerated-content"` if CNXML does not have any link text
    - See https://openstax.atlassian.net/wiki/spaces/CE/pages/1759707137/Pipeline+Pipeline+Task+Definitions#Git-Links examples
1. Fetch exercise JSON and TeX Math from exercises.openstax.org and convert it to HTML and MathML
    - Check if the TeX to MathML is dead. Because the code supposedly calls the MMLCloud API: https://github.com/openstax/cnx-epub/blob/master/cnxepub/formatters.py#L328
1. When injected exercises have a cnx-context tag then resolve whether the exercise context should like to an element on this page, another page in this book, or a page in another book: https://github.com/openstax/cnx-epub/blob/master/cnxepub/formatters.py#L382
1. Write the book out using this template (Do we need most of this?): https://github.com/openstax/cnx-epub/blob/master/cnxepub/formatters.py#L602
1. A ToC is added to the top of the gigantic XHTML file: https://github.com/openstax/cnx-epub/blob/master/cnxepub/formatters.py#L932


**Validation:**

1. XHTML validator should pass for every assembled XHTML file
1. Some RNG to validate the root elements (unit, chapter, page).


## git-bake

CS-Styles takes it over from here and bakes the big XHTML file using a Ruby recipe

**Validation:**

- XHTML validator
- The top elements that the disassembler looks for should be defined in an RNG


## git-bake-meta

Create a `{slug}.baked-metadata.json` which contains...

```js
{
    "{page_uuid}": { abstract: "...", revised: "2022-..." }
    "{book_uuid}@{ver}": { 
        id: "{book_uuid}",
        title: "Algebra", 
        revised: "2022-...", 
        slug: "algebra-trig",
        version: "359e7eb",
        language: "en",
        license: {
            url: "http://creativecommons.org/licenses/by/1.0",
            name: "Creative Commons Attribution License"
        },
        tree: {
            id: "{uuid}",
            title: "Title of the chapter",
            contents: [
                id: "",
                title: "<span>Title with</span> Markup",
                slug: "1-1-addition"
            ]
        }
    }
}
```

**Validation:**

- JSONSchema on each generated book's JSON file.
- Maybe XHTML validation on each Baked XHTML file.


## git-link

For links to other books, this step adds attributes on the link so REX will be able to choose the right book to link to:

- `data-book-uuid="..."`
- `data-book-slug="..."`
- `data-page-slug="..."`


**Validation:**

Whatever REX expects these files to have.

## Output-specific

This is the end of the common parts of the pipeline. Here things diverge for each output.


# Required languages

- Ruby for baking
- Something that supports parsing XML/JSON **with source line/column numbers** (Sourcemaps) to run all the other steps

## Validation

- TypeScript for POET CLI
- Java: for XHTML and RNG validation