from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter


LANG_CHOICE = (
    ('c', 'C'),
    ('cpp', 'C++11'),
    ('python', 'Python 3'),
    ('java', 'Java 8'),
    ('cc14', 'C++14'),
    ('cs', 'C#'),
    ('py2', 'Python 2'),
    ('php', 'PHP 7'),
    ('perl', 'Perl'),
    ('hs', 'Haskell'),
    ('js', 'Javascript'),
    ('ocaml', 'OCaml'),
    ('pypy', 'PyPy'),
    ('pas', 'Pascal'),
    ('rs', 'Rust'),
    ('scala', 'Scala')
)

LANG_REGULAR_NAME = (
    ('cc14', 'cpp'),
    ('cs', 'csharp'),
    ('py2', 'python'),
    ('pas', 'pascal'),
    ('rs', 'rust'),
)


LANG_EXT = (
    ('c', 'c'),
    ('cpp', 'cpp'),
    ('python', 'py'),
    ('java', 'java'),
    ('cc14', 'cpp'),
    ('cs', 'cs'),
    ('py2', 'py'),
    ('php', 'php'),
    ('perl', 'pl'),
    ('hs', 'hs'),
    ('js', 'js'),
    ('ocaml', 'ml'),
    ('pypy', 'py'),
    ('pas', 'pas'),
    ('rs', 'rs'),
    ('scala', 'scala'),
)


def transform_code_to_html(code, lang):
    return highlight(code, get_lexer_by_name(dict(LANG_REGULAR_NAME).get(lang, lang)), HtmlFormatter())
