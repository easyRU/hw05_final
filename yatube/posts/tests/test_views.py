from datetime import date

from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Follow, Group, Post, User

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


class PostsPagesTests(TestCase):
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

    def form_have_good_fields(self, response):
        '''Контекст для проверки страниц с формами.'''
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def check_all_context(self, response):
        self.assertTrue(response.context)
        response_post = response.context['page_obj'][0]
        self.assertEqual(response_post.author, self.post.author)
        self.assertEqual(response_post.group, self.post.group)
        self.assertEqual(response_post.text, self.post.text)
        self.assertEqual(response_post.pub_date, self.post.pub_date)
        self.assertEqual(response_post.image, self.post.image)

    def test_pages_uses_correct_template(self):
        '''URL-адрес использует соответствующий шаблон.'''
        # Собираем в словарь пары 'имя_html_шаблона: reverse(name)'
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse('posts:group_list',
                     kwargs={
                         'slug': self.group.slug
                     })): 'posts/group_list.html',
            (reverse('posts:profile',
                     kwargs={
                         'username': self.post.author.username
                     })): 'posts/profile.html',
            (reverse('posts:post_detail',
                     kwargs={
                         'post_id': self.post.id
                     })): 'posts/post_detail.html',
            (reverse('posts:post_edit',
                     kwargs={
                         'post_id': self.post.id
                     })): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_pages_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        self.check_all_context(response)

    def test_group_list_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertIn('page_obj', response.context)
        self.check_all_context(response)

        self.assertIn('group', response.context)
        response_group = response.context.get('group')
        self.assertEqual(response_group, self.group)

    def test_profile_page_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.post.author.username}))
        self.check_all_context(response)

    def test_create_post_show_correct_context(self):
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст 2',
            'group': self.group.id,
            'image': forms.fields.ImageField,
        }
        response = self.authorized_client.post(reverse('posts:post_create'),
                                               data=form_data,
                                               follow=True)

        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': self.post.author.username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(Post.objects.filter(text='Тестовый текст 2',
                                            group=self.group.id,).exists())

    def test_post_detail_pages_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))
        self.assertEqual(response.context['post'].text, self.post.text)
        post_count = response.context['post'].author.posts.count()
        self.assertEqual(self.post.author.posts.count(), post_count)

    def test_form_create_pages_show_correct_context(self):
        '''Проверка формы создания поста.'''
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.form_have_good_fields(response)

    def test_form_edit_pages_show_correct_context(self):
        '''Проверка формы редактирования поста.'''
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.form_have_good_fields(response)

    def test_post_not_another_group(self):
        '''Проверка пост не попал не в свою группу'''
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group_second.slug})
        )
        self.assertEqual(len(response.context.get('page_obj').object_list), 0)

    def test_cache_index(self):
        response = self.authorized_client.get(reverse('posts:index'))
        form_data_for_cache = {
            'text': 'Проверка кэша',
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data_for_cache,
            follow=True
        )
        self.assertNotContains(response, form_data_for_cache['text'])
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertContains(response, form_data_for_cache['text'])


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug')
        cls.follower = User.objects.create(
            username='follower',
        )
        cls.not_follower = User.objects.create(
            username='not_follower',
        )
        cls.following = User.objects.create(
            username='following',
        )
        cls.post = Post.objects.create(
            author=cls.following,
            text='Тестовый текст',
            pub_date=date.today(),
            group=cls.group,
            image=uploaded
        )

    def setUp(self):
        cache.clear()

        self.follower_client = Client()
        self.follower_client.force_login(self.follower)

        self.not_follower_client = Client()
        self.not_follower_client.force_login(self.not_follower)

    def test_follow_page(self):
        Follow.objects.get_or_create(user=self.follower, author=self.following)
        count_posts_follower = Follow.objects.filter(
            user=self.follower, author=self.following
        ).count()

        self.assertEqual(count_posts_follower, 1)

        count_posts_not_follower = Follow.objects.filter(
            user=self.not_follower, author=self.following
        ).count()

        self.assertEqual(count_posts_not_follower, 0)

    def test_follow(self):
        self.follower_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': FollowTests.following}
            )
        )
        self.assertEqual(Follow.objects.count(), 1)

    def test_unfollow(self):
        if (Follow.objects.get_or_create(user=self.follower,
                                         author=self.following))[1]:
            self.follower_client.get(
                reverse(
                    'posts:profile_unfollow',
                    kwargs={'username': FollowTests.following}
                )
            )
        self.assertEqual(Follow.objects.count(), 0)
