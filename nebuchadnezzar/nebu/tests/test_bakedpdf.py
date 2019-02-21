from os import scandir
from pathlib import Path

from lxml import etree

from nebu.bakedpdf import assembler


class TestAssembler(object):

    def test_assembler(self, datadir, tmpcwd):
        """assert that `expected` etree contains certain elements in the
        expected xpath position, containing the expected text.
        """
        source_dir = datadir / 'col11562_1.23_complete'
        out_dir = tmpcwd
        out_fname = 'IT_WORKS'
        titles_xpath = '//*[@data-type="document-title"]/text()'

        runner = assembler(source_dir, out_dir, out_fname=out_fname)
        runner()

        # it generates an xhtml file with the given filename
        expected_output_file = (out_dir / (out_fname + '.xhtml')).open('rb')

        """The titles from source modules show up in the output file"""

        # locate every module file in the source dir
        m_name = '/index.cnxml.html'
        modules = [Path((m.path + m_name)) for m in scandir(str(source_dir))
                   if m.name.startswith('m')]
        mod_trees = [etree.parse(m.open('rb')) for m in modules]
        titles = list([tree.xpath(titles_xpath)[0] for tree in mod_trees])

        output_titles = etree.parse(expected_output_file).xpath(titles_xpath)

        for title in titles:
            assert title in output_titles

        # NOTE: When a module's index.cnxml.html file cannot be found in the
        # source dir, we currently replace it with DATA_WHEN_MODULE_NOT_FOUND
        # in the assembled single html output.

        # TODO: Probably should look for at least part of the modules' contents
        #       in the output contents.

        # FIXME: Perhaps we should assert that images are referred to correctly
