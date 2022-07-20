from datetime import date
from http import HTTPStatus

from django.core.cache import cache
from django.test import Client, TestCase
from posts.models import Group, Post, UserModel


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = UserModel.objects.create_user(username='auth')
        cls.user_no_name = UserModel.objects.create_user(username='HasNoName')

        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug')

        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            pub_date=date.today(),
            group=cls.group
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_no_name)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names_for_all = {
            'posts/index.html': '/',
            'posts/profile.html': f'/profile/{self.author}/',
            'posts/group_list.html': f'/group/{self.group.slug}/',
            'posts/post_detail.html': f'/posts/{self.post.id}/',
        }

        for template, address in templates_url_names_for_all.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def create_not_authorized_client_page(self):
        """Редактирование доступно только автору поста"""
        response = self.guest_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_not_page(self):
        """Страница не существует."""
        response = self.guest_client.get('/unexisting-page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def create_page_anonymous(self):
        """Создание поста неавторизованным пользователем"""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/users/login/'
        )

    def test_urls_status_OK(self):
        templates_url_names_for_OK = (
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.author}/',
            f'/posts/{self.post.id}/'
        )

        for address in templates_url_names_for_OK:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def create_page(self):
        """Создание поста авторизованным пользователем"""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def create_authorized_client_page(self):
        """Редактирование доступно автору поста"""
        response = self.authorized_author.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.OK)
