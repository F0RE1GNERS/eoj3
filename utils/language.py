from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter


LANG_CHOICE = (
    ('c', 'C'),
    ('cpp', 'C++11'),
    ('cc14', 'C++14'),
    ('cc17', 'C++17'),
    ('py2', 'Python 2'),
    ('python', 'Python 3'),
    ('pypy', 'PyPy'),
    ('pypy3', 'PyPy 3'),
    ('java', 'Java 8'),
    ('pas', 'Pascal'),
    ('text', 'Text')
)

LANG_REGULAR_NAME = (
    ('cc14', 'cpp'),
    ('cc17', 'cpp'),
    ('py2', 'python'),
    ('pypy3', 'python'),
    ('pas', 'pascal'),
    ('', 'text')
)

LANG_EXT = (
    ('c', 'c'),
    ('cpp', 'cpp'),
    ('python', 'py'),
    ('java', 'java'),
    ('cc14', 'cpp'),
    ('cc17', 'cpp'),
    ('py2', 'py'),
    ('pypy', 'py'),
    ('pypy3', 'py'),
    ('pas', 'pas'),
    ('text', 'txt'),
)


def transform_code_to_html(code, lang):
    return highlight(code, get_lexer_by_name(dict(LANG_REGULAR_NAME).get(lang, lang)), HtmlFormatter())
