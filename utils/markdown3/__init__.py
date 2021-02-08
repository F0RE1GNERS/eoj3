import markdown
from django.shortcuts import HttpResponse

from . import mdx_downheader
from . import semantic


def convert(text):
  md = markdown.Markdown(
    extensions=[mdx_downheader.makeExtension(levels=2),
                # mdx_math.makeExtension(enable_dollar_delimiter=True, add_preview=False),
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
  from utils.jinja2.filters import xss_filter
  return HttpResponse(xss_filter(convert(request.POST.get('text', ''))))
