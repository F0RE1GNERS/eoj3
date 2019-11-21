from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage, Page, InvalidPage
from django.http import Http404
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView


class EndlessPaginator(Paginator):

  @cached_property
  def count(self):
    return 0

  @cached_property
  def num_pages(self):
    return 0

  def validate_number(self, number):
    """
    Validates the given 1-based page number.
    """
    try:
      number = int(number)
    except (TypeError, ValueError):
      raise PageNotAnInteger('That page number is not an integer')
    if number < 1:
      raise EmptyPage('That page number is less than 1')
    return number

  def page(self, number):
    """
    Returns a Page object for the given 1-based page number.
    """
    number = self.validate_number(number)
    bottom = (number - 1) * self.per_page
    top = bottom + self.per_page
    return self._get_page(self.object_list[bottom:top], number, self)

  def _get_page(self, *args, **kwargs):
    """
    Returns an instance of a single page.

    This hook can be used by subclasses to use an alternative to the
    standard :cls:`Page` object.
    """
    return EndlessPage(*args, **kwargs)


class EndlessPage(Page):

  def __repr__(self):
    return '<Page %s of Endless Page>' % self.number

  def start_index(self):
    return (self.paginator.per_page * (self.number - 1)) + 1

  def end_index(self):
    if self.number == self.paginator.num_pages:
      return self.paginator.count
    return self.number * self.paginator.per_page


class EndlessListView(ListView):
  paginator_class = EndlessPaginator

  def paginate_queryset(self, queryset, page_size):
    """
    Paginate the queryset, if needed.
    """
    paginator = self.get_paginator(
      queryset, page_size, orphans=self.get_paginate_orphans(),
      allow_empty_first_page=self.get_allow_empty())
    page_kwarg = self.page_kwarg
    page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
    try:
      page_number = int(page)
    except ValueError:
      raise Http404(_("Page can not be converted to an int."))
    try:
      page = paginator.page(page_number)
      return (paginator, page, page.object_list, page.has_other_pages())
    except InvalidPage as e:
      raise Http404(_('Invalid page (%(page_number)s): %(message)s') % {
        'page_number': page_number,
        'message': str(e)
      })
