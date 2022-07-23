from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, User

COUNT_POSTS_ON_SECOND_PAGES = settings.NUM_POSTS // 2


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create(username='auth', )

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug')

        post_count = settings.NUM_POSTS + COUNT_POSTS_ON_SECOND_PAGES

        post_list = [
            Post(
                text=f"Текст поста {i}",
                author=cls.author,
                group=cls.group
            ) for i in range(post_count)
        ]
        Post.objects.bulk_create(post_list)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_first_page_contains_records(self):
        """Тестируем первую страницу пагинатора"""
        paginator_pages = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'page_obj',
            reverse('posts:profile',
                    kwargs={'username': self.author}): 'page_obj',
        }
        for reverse_name, obj in paginator_pages.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(len(response.context[obj]),
                                 settings.NUM_POSTS)

    def test_second_page_contains_five_records(self):
        paginator_pages = {
            reverse('posts:index'): 'page_obj',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}): 'page_obj',
            reverse('posts:profile',
                    kwargs={'username': self.author}): 'page_obj',
        }
        for reverse_name, obj in paginator_pages.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name + "?page=2")
                self.assertEqual(len(response.context[obj]), 
                                 COUNT_POSTS_ON_SECOND_PAGES)
