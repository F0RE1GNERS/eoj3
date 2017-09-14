from bs4 import BeautifulSoup
import markupsafe
import traceback


RULES = {
    # tag: (class list, [default, optional])
    'table': (['ui', 'table', 'center', 'aligned', 'celled'], []),
    'img': (['ui', 'image', 'centered'], ['large', 'medium', 'fluid', 'mini', 'tiny', 'small', 'big', 'huge', 'massive'])
}


def semantic_processor(text):
    try:
        soup = BeautifulSoup(str(text), "html.parser")
        for child in soup.recursiveChildGenerator():
            if child.name in RULES.keys():
                rule = RULES[child.name]
                child.attrs.setdefault('class', [])
                child.attrs['class'].extend(rule[0])
                if rule[1] and all(size not in child.attrs['class'] for size in rule[1]):
                    child.attrs['class'].append(rule[1][0])
        return markupsafe.Markup(soup)
    except:
        traceback.print_exc()
        return text
