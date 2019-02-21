from lxml import etree

from cnxepub.models import Binder, TranslucentBinder, Document
from cnxepub.formatters import SingleHTMLFormatter


__all__ = (
    'assembler',
)


"""`Document`s require that modules contain a body tag, but this assembler
allows for building a single/collection HTML with empty modules, therefore
we must use this variable in place of data when building `Document` models.
When updating this also update the tests.
"""
DATA_WHEN_MODULE_NOT_FOUND = "<body>Module with id {} goes here.</body>"


def assembler(source_dir, out_dir='.', out_fname='collection'):
    """Assembles a single HTML file from a collection of module HTML files, a
    CollXML file defines their ordering/structure.
    """
    out_loc = out_dir / (out_fname + '.xhtml')
    collxml = (source_dir / 'collection.xml').open('rb')

    def main():
        binder = collxml_to_binder(collxml)

        with out_loc.open('w') as f:
            f.write(str(SingleHTMLFormatter(binder)))

    def collxml_to_binder(collxml):
        tags = [
            '{http://cnx.rice.edu/collxml}subcollection',
            '{http://cnx.rice.edu/collxml}collection',
            '{http://cnx.rice.edu/collxml}module',
            '{http://cnx.rice.edu/mdml}title',
        ]

        collxml_etree = etree.iterparse(collxml, events=('start', 'end'),
                                        tag=tags, remove_blank_text=True)

        root_adapter = build_adapters_tree(collxml_etree)

        binder = root_adapter.to_model()
        return binder

    def build_adapters_tree(collxml_etree):
        """Binders require bottom-up construction (sub-binders are passed into
        the constructor). So we'll (1) parse the element tree top-down and
        store the needed information in Adapter nodes and then (2) use
        post-order traversalon the Adapter tree to construct Binders from their
        sub-binders.
        """
        node = None  # the node currently being parsed

        for event, element in collxml_etree:
            tag = element.tag.split('}')[-1]  # tag without namespace

            if tag == 'title':
                assert node  # adapter w/ 'collection' tag should already exist
                node.title = element.text

            elif event == 'start':
                new_ = Adapter(tag, element.attrib)
                if node:
                    node.add_child(new_)
                node = new_

            elif event == 'end':
                node = node.parent

        # After the last `end` event is processed, `node` is the root node
        root_node = node
        return root_node

    class Adapter(object):
        def __init__(self, tag, attrib, title=''):
            self.tag = tag
            self.attrib = dict(attrib).copy()
            self.title = title
            self.parent = self
            self.children = []

        def add_child(self, child):
            child.parent = self
            self.children.append(child)
            return self

        def __iter__(self):
            return iter(self.children)

        def iter(self, tag='*'):
            if tag == '*' or self.tag == tag:
                yield self

            for child in self:
                yield from child.iter(tag)

        def to_model(self):
            ch_models = [child.to_model() for child in self.children]
            meta = {'title': self.title}

            if self.tag == 'collection':
                return Binder(self.title, nodes=ch_models, metadata=meta)
            elif self.tag == 'subcollection':
                return TranslucentBinder(nodes=ch_models, metadata=meta)
            elif self.tag == 'module':
                module_id = self.attrib.get('document')
                data = find_doc_data(module_id)
                meta['license_url'] = None  # required by `Document`
                return Document(module_id, data, metadata=meta)
            else:
                raise Exception('unrecognized tag: {}'.format(self.tag))

    def find_doc_data(module_id):
        """Locates and reads a cnxml file/module with given `module_id`
        """
        try:
            mod_loc = source_dir / module_id / 'index.cnxml.html'
            with mod_loc.open('rb') as fb:
                doc_data = fb.read()
            return doc_data
        except FileNotFoundError:
            # FIXME: create and raise a custom exception, write log entry, ?
            return DATA_WHEN_MODULE_NOT_FOUND.format(module_id)

    return main
