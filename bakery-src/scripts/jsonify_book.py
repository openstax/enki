import json
import sys
from glob import glob
from os.path import basename

from .profiler import timed
from . import excepthook


excepthook.attach(sys)


@timed
def main():
    book_dir, out_dir = sys.argv[1:3]

    files = [basename(x).rstrip(".xhtml") for x in glob(f"{book_dir}/*.xhtml")]

    json_data = {}

    for path in files:
        try:
            with open(f"{book_dir}/{path}-metadata.json", "r") as meta_part:
                json_data = json.load(meta_part)
        except FileNotFoundError:
            json_data = {}

        with open(f"{book_dir}/{path}.xhtml", "r") as book_part:
            content = book_part.read()
            json_data["content"] = str(content)

        with open(f"{out_dir}/{path}.json", 'w') as outfile:
            json.dump(json_data, outfile)

        with open(f"{out_dir}/{path}.xhtml", 'w') as outfile:
            outfile.write(json_data["content"])


if __name__ == "__main__":  # pragma: no cover
    main()
