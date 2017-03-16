from django import template

register = template.Library()


def paginator(context, adjacent_pages=3):
    display_pages = adjacent_pages * 2 + 1
    page_obj = context['page_obj']
    num = page_obj.paginator.num_pages
    cur = page_obj.number
    if num <= display_pages:
        page_numbers = range(1, num + 1)
    elif cur - adjacent_pages <= 1:
        page_numbers = range(1, display_pages + 1)
    elif cur + adjacent_pages >= num:
        page_numbers = range(num - display_pages + 1, num + 1)
    else:
        page_numbers = range(cur - adjacent_pages, cur + adjacent_pages + 1)
    return {
        'page_obj': page_obj,
        'page_numbers': page_numbers,
        'show_first': 1 not in page_numbers,
        'show_last': num not in page_numbers,
    }

register.inclusion_tag('components/pagination.html', takes_context=True)(paginator)
