from datetime import date

from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, UserModel


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = UserModel.objects.create(username='auth', )

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug')

        post_count = 15
        for _ in range(post_count):
            Post.objects.create(
                author=cls.author,
                text='Текст поста',
                pub_date=date.today(),
                group=cls.group)

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
                self.assertEqual(len(response.context[obj]), 10)
