from django.core.paginator import Paginator


def split_pages(posts, request):
    num_posts = 10
    paginator = Paginator(posts, num_posts)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
