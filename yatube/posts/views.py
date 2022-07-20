from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, UserModel
from .utils import split_pages


@cache_page(20, key_prefix='index_page')
def index(request):
    posts = Post.objects.select_related('group', 'author').all()
    context = {
        'page_obj': split_pages(posts, request),
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related("author", "group")
    context = {
        'group': group,
        'page_obj': split_pages(posts, request),
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(UserModel, username=username)
    posts = Post.objects.filter(author=author)
    user = request.user
    following = (request.user.is_authenticated
                 and(author.following.filter(user=user))
                 and(user!=author))
    context = {
        'page_obj': split_pages(posts, request),
        'posts': posts,
        'author': author,
        "following": following
    }
    template = 'posts/profile.html'
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(
        Post.objects.select_related('group', 'author'), pk=post_id)
    form = CommentForm()
    comments = post.comments.all()
    following = (
        request.user.is_authenticated
        and Follow.objects.filter(
            user=request.user, author=post.author
        ).exists()
    )
    context = {'post': post,
               'form': form,
               'comments': comments, 
               "following": following}
    return render(request, 'posts/post_detail.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def post_create(request):
    template = "posts/create_post.html"
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
        )
    if not form.is_valid():
        context = {"form": form}
        return render(request, template, context)
    new_post = form.save(commit=False)
    new_post.author = request.user
    new_post.save()
    return redirect("posts:profile", username=request.user)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if not form.is_valid():
        is_edit = True
        context = {
            'form': form,
            'is_edit': is_edit
        }
        return render(request, 'posts/create_post.html', context)
    form.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    user = request.user
    author = get_object_or_404(UserModel, username=username)
    if user != author:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    user = request.user
    author = get_object_or_404(UserModel, username=username)
    if user != author:
        Follow.objects.filter(user=user, author=author).delete()
    return redirect('posts:profile', username=username)
