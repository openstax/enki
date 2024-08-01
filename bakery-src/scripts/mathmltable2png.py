import sys
from pathlib import Path
from .profiler import timed

from lxml import etree

from bakery_scripts.mathml2png import convert_math


@timed
def main():  # pragma: no cover
    '''main function
    1. Argument: XHTML file with MathML mtable equations
    2. Argument: resource folder
    3. Argument: destination XHTML file with MathML->PNG converted images
    '''
    xhtml_file = str(Path(sys.argv[1]).resolve(strict=True))
    resources_dir = str(Path(sys.argv[2]).resolve(strict=True))
    result_xhtml_file = sys.argv[3]
    if sys.version_info[0] < 3:
        raise Exception("Must be using Python 3")
    xhtml = etree.parse(xhtml_file)
    ns = {"h": "http://www.w3.org/1999/xhtml",
          "m": "http://www.w3.org/1998/Math/MathML"}

    xpath = '//h:math[descendant::h:mtable]|//m:math[descendant::m:mtable]'
    convert_math(xhtml.xpath(xpath, namespaces=ns), resources_dir)
    
    with open(result_xhtml_file, 'wb') as out:
        out.write(etree.tostring(xhtml, encoding='utf8', pretty_print=False))


if __name__ == "__main__":  # pragma: no cover
    main()
