import shutil
import tempfile
from datetime import date
from http import HTTPStatus

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user_not_author = User.objects.create_user(username='not_auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.form = PostForm

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client_not_author = Client()
        self.authorized_client_not_author.force_login(self.user_not_author)

    def test_create_post(self):
        '''Проверяем создание поста формой.'''
        post_count = Post.objects.count()

        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(reverse(
            'posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.user})
        )
        self.assertEqual(Post.objects.count(), post_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый пост',
                group=self.group.id,
                image='posts/small.gif'
            ).exists()
        )

    def not_registred_user_cant_create_post(self):
        ''' Незарегистрированный пользователь не может создать пост'''
        post_count = Post.objects.count()
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый пост',
            'group': self.group.id,
            'image': uploaded,
        }
        self.guest_client.post(reverse(
            'posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count)

    def test_edit_post(self):
        '''Проверяем редактирование поста формой.'''
        form_data = {
            'text': 'Тестовый текст для редактирования поста',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        new_form_data = {
            'text': 'Я автор и редактирую пост',
        }
        post = Post.objects.all()[0]
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=new_form_data,
            follow=True
        )
        post = Post.objects.all()[0]
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': post.id}))

        self.assertEqual(post.text, new_form_data['text'])

    def not_author_cant_edit_post(self):
        '''Не автор поста не может редактировать пост'''
        new_form_data_not_author = {
            'text': 'Я не автор и хочу поменять твой пост',
        }
        post = Post.objects.last()
        self.authorized_client_not_author.post(
            reverse('posts:post_edit', kwargs={'post_id': post.id}),
            data=new_form_data_not_author,
            follow=True
        )
        self.assertNotEqual(post.text, new_form_data_not_author['text'])


class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            group=cls.group,
            text='Текст поста'
        )

    def test_label(self):
        label_text = PostFormTests.form.fields['text'].label
        self.assertEqual(label_text, 'Текст поста')
        label_group = PostFormTests.form.fields['group'].label
        self.assertEqual(label_group, 'Группа')

    def test_help_text(self):
        help_text = PostFormTests.form.fields['text'].help_text
        self.assertEqual(help_text, 'Текст нового поста')
        help_text_group = PostFormTests.form.fields['group'].help_text
        self.assertEqual(
            help_text_group,
            'Пост будет относиться к этой группе'
        )


class CommentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.author = User.objects.create(username='auth', )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug'
        )
        cls.group_second = Group.objects.create(
            title='Тестовый заголовок2',
            description='Тестовое описание2',
            slug='test-slug2'
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            pub_date=date.today(),
            group=cls.group,
            image=uploaded
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_add_comment(self):
        '''комментарий авторизованного пользователя создался'''
        post = Post.objects.last()
        form_data = {
            'text': 'test comment',
            'post': post,
            'author': self.authorized_client,
        }

        comments_before_authorized_client = post.comments.all().count()
        response_post = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=False,
        )
        self.assertEqual(response_post.status_code, HTTPStatus.FOUND)
        comments_after_authorized_client = post.comments.all().count()
        self.assertNotEqual(comments_before_authorized_client,
                            comments_after_authorized_client)

    def not_registred_user_dont_create_comment(self):
        '''Незарегистрированный пользователь не создает комментарий'''
        post = Post.objects.last()
        form_data = {
            'text': 'test comment',
            'post': post,
            'author': self.authorized_client,
        }
        comments_before_guest_client = post.comments.all().count()
        self.guest_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=False,
        )
        comments_before_after_guest_client = post.comments.all().count()
        self.assertEqual(comments_before_guest_client,
                         comments_before_after_guest_client)
