# What are assembled and raw?
It can be useful to compare how the content changes throughout assemble. These two directories represent the converted content at the beginning (raw) and end (assembled) for the assembly process.

## More details about assemble
* [BookPart.collection_from_file](../../models/book_part.py) for details about how the tree is created.
* [assemble.collection_to_assembled_xhtml](../../cli/assemble.py) for details about how the collection xhtml is mutated during assembly.

## Raw, created by test_formatters.py, is what the xhtml looks like BEFORE
* [fetch_insert_includes](../../formatters.py)
* [resolve_module_links](../../formatters.py)
* [update_ids](../../formatters.py)

## Assembled, created by test_assemble.py, is what the xhtml looks like at the end of assemble
