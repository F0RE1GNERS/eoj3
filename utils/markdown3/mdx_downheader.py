from markdown import Extension
from markdown.treeprocessors import Treeprocessor


class DownHeaderTreeProcessor(Treeprocessor):
    def __init__(self, levels):
        self.levels = levels
        super(DownHeaderTreeProcessor, self).__init__()

    def run(self, doc):
        for elem in doc:
            if elem.tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                original_level = int(elem.tag[-1])
                level = original_level + int(self.levels)
                level = min(6, max(1, level))
                elem.tag = 'h' + str(level)


class DownHeaderExtension(Extension):
    def __init__(self, *args, **kwargs):
        self.config = {
            'levels': [1, 'downgrade headings this many levels'],
        }
        super(DownHeaderExtension, self).__init__(**kwargs)

    def extendMarkdown(self, md, md_globals):
        if 'downheader' not in md.treeprocessors.keys():
            treeprocessor = DownHeaderTreeProcessor(self.getConfig('levels'))
            md.treeprocessors.add('downheader', treeprocessor, '_end')


def makeExtension(*args, **kwargs):
    return DownHeaderExtension(*args, **kwargs)
