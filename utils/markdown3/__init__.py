import markdown
from . import mdx_downheader
from . import mdx_math
from . import semantic
from django.shortcuts import HttpResponse


def convert(text):
    md = markdown.Markdown(
        extensions=[mdx_downheader.makeExtension(levels=2),
                    mdx_math.makeExtension(enable_dollar_delimiter=True, add_preview=False),
                    'fenced_code',
                    'codehilite',
                    'markdown.extensions.attr_list',
                    'nl2br',
                    'tables',
                    'markdown.extensions.smarty'
                    ]
    )
    return semantic.semantic_processor(md.convert(text))


def markdown_convert_api(request):
    return HttpResponse(convert(request.POST.get('text', '')))
