# -*- coding: utf-8 -*-

'''
Math extension for Python-Markdown
==================================
Adds support for displaying math formulas using [MathJax](http://www.mathjax.org/).
Author: 2015-2017, Dmitry Shachnev <mitya57@gmail.com>.
'''

import markdown
from markdown.util import AtomicString, etree

class MathExtension(markdown.extensions.Extension):
    def __init__(self, *args, **kwargs):
        self.config = {
            'enable_dollar_delimiter': [False, 'Enable single-dollar delimiter'],
            'add_preview': [False, 'Add a preview node before each math node'],
        }
        super(MathExtension, self).__init__(*args, **kwargs)

    def extendMarkdown(self, md, md_globals):
        def _wrap_node(node, preview_text, wrapper_tag):
            if not self.getConfig('add_preview'):
                return node
            preview = etree.Element('span', {'class': 'MathJax_Preview'})
            preview.text = AtomicString(preview_text)
            wrapper = etree.Element(wrapper_tag)
            wrapper.extend([preview, node])
            return wrapper

        def handle_match_inline(m):
            node = etree.Element('script')
            node.set('type', 'math/tex')
            node.text = AtomicString(m.group(3))
            return _wrap_node(node, ''.join(m.group(2, 3, 4)), 'span')

        def handle_match(m):
            node = etree.Element('script')
            node.set('type', 'math/tex; mode=display')
            if '\\begin' in m.group(2):
                node.text = AtomicString(''.join(m.group(2, 4, 5)))
                return _wrap_node(node, ''.join(m.group(1, 2, 4, 5, 6)), 'div')
            else:
                node.text = AtomicString(m.group(3))
                return _wrap_node(node, ''.join(m.group(2, 3, 4)), 'div')

        inlinemathpatterns = (
            markdown.inlinepatterns.Pattern(r'(?<!\\|\$)(\$)([^\$]+)(\$)'),  #  $...$
            markdown.inlinepatterns.Pattern(r'(?<!\\)(\\\()(.+?)(\\\))')     # \(...\)
        )
        mathpatterns = (
            markdown.inlinepatterns.Pattern(r'(?<!\\)(\$\$)([^\$]+)(\$\$)'), # $$...$$
            markdown.inlinepatterns.Pattern(r'(?<!\\)(\\\[)(.+?)(\\\])'),    # \[...\]
            markdown.inlinepatterns.Pattern(r'(?<!\\)(\\begin{([a-z]+?\*?)})(.+?)(\\end{\3})')
        )
        if not self.getConfig('enable_dollar_delimiter'):
            inlinemathpatterns = inlinemathpatterns[1:]
        for i, pattern in enumerate(inlinemathpatterns):
            pattern.handleMatch = handle_match_inline
            md.inlinePatterns.add('math-inline-%d' % i, pattern, '<escape')
        for i, pattern in enumerate(mathpatterns):
            pattern.handleMatch = handle_match
            md.inlinePatterns.add('math-%d' % i, pattern, '<escape')

def makeExtension(*args, **kwargs):
    return MathExtension(*args, **kwargs)