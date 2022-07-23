from django.conf import settings
from django.core.paginator import Paginator


def split_pages(posts, request):
    paginator = Paginator(posts, settings.NUM_POSTS)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
