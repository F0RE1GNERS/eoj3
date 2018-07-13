from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter


LANG_CHOICE = (
    ('c', 'C'),
    ('cpp', 'C++11'),
    ('python', 'Python 3'),
    ('java', 'Java 8'),
    ('cc14', 'C++14'),
    ('cc17', 'C++17'),
    ('cs', 'C#'),
    ('py2', 'Python 2'),
    ('scipy', 'Python (SCI)'),
    ('php', 'PHP 7'),
    ('perl', 'Perl'),
    ('hs', 'Haskell'),
    ('js', 'Javascript'),
    ('ocaml', 'OCaml'),
    ('pypy', 'PyPy'),
    ('pypy3', 'PyPy 3'),
    ('pas', 'Pascal'),
    ('rs', 'Rust'),
    ('scala', 'Scala'),
    ('text', 'Text')
)

LANG_REGULAR_NAME = (
    ('cc14', 'cpp'),
    ('cc17', 'cpp'),
    ('cs', 'csharp'),
    ('py2', 'python'),
    ('scipy', 'python'),
    ('pypy3', 'pypy'),
    ('pas', 'pascal'),
    ('rs', 'rust'),
)


LANG_EXT = (
    ('c', 'c'),
    ('cpp', 'cpp'),
    ('python', 'py'),
    ('java', 'java'),
    ('cc14', 'cpp'),
    ('cc17', 'cpp'),
    ('cs', 'cs'),
    ('py2', 'py'),
    ('scipy', 'py'),
    ('php', 'php'),
    ('perl', 'pl'),
    ('hs', 'hs'),
    ('js', 'js'),
    ('ocaml', 'ml'),
    ('pypy', 'py'),
    ('pypy3', 'py'),
    ('pas', 'pas'),
    ('rs', 'rs'),
    ('scala', 'scala'),
    ('text', 'txt'),
)


def transform_code_to_html(code, lang):
    return highlight(code, get_lexer_by_name(dict(LANG_REGULAR_NAME).get(lang, lang)), HtmlFormatter())
