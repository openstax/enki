import json
import sys
from pathlib import Path


from . import utils
from . import cnx_models
from . import html_parser


def main():
    input_assembled_file = Path(sys.argv[1]).resolve(strict=True)
    uuid_to_revised_path = Path(sys.argv[2]).resolve(strict=True)
    output_file_path = sys.argv[3]

    with open(uuid_to_revised_path, 'r') as f:
        uuid_to_revised_map = json.load(f)

    json_data = {}

    with open(input_assembled_file, "r") as in_file:
        binder = html_parser.reconstitute(in_file)

    for doc in cnx_models.flatten_to_documents(binder):
        abstract = doc.metadata.get("summary")
        # Use the map revised value if available, otherwise expect it from the
        # metadata parsed from the assembled XHTML
        revised = uuid_to_revised_map.get(doc.id) or doc.metadata["revised"]
        json_data[doc.ident_hash] = {
            "abstract": abstract,
            "revised": utils.ensure_isoformat(revised)
        }

    with open(output_file_path, "w") as out_file:
        json.dump(json_data, out_file)


if __name__ == "__main__":  # pragma: no cover
    main()
