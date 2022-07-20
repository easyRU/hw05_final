from datetime import date

from django import forms
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Follow, Group, Post, UserModel

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
        cls.author = UserModel.objects.create(username='auth', )
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

    def all_context(self, response):
        self.assertTrue(response.context)
        response_post = response.context['page_obj'][0]
        self.assertEqual(response_post.author, self.post.author)
        self.assertEqual(response_post.group, self.post.group)
        self.assertEqual(response_post.text, self.post.text)
        self.assertEqual(response_post.pub_date, self.post.pub_date)
        self.assertEqual(response_post.image, self.post.image)

    def test_index_pages_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        self.all_context(response)

    def test_group_list_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertIn('page_obj', response.context)
        self.all_context(response)

        self.assertIn('group', response.context)
        response_group = response.context.get('group')
        self.assertEqual(response_group, self.group)

    def test_profile_page_show_correct_context(self):
        response = self.authorized_client.get(reverse(
            'posts:profile', kwargs={'username': self.post.author.username}))
        self.all_context(response)

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

    def form_context(self, response):
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

    def test_form_create_pages_show_correct_context(self):
        '''Проверка формы создания поста.'''
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.form_context(response)

    def test_form_edit_pages_show_correct_context(self):
        '''Проверка формы редактирования поста.'''
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.form_context(response)

    def test_post_not_another_group(self):
        '''Проверка пост не попал не в свою группу'''
        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group_second.slug})
        )
        self.assertEqual(len(response.context.get('page_obj').object_list), 0)

    def test_create_post(self):
        '''Проверка вновь созданной группы на наличие постов'''
        posts = Post.objects.select_related('group')\
            .filter(id=self.group_second.id)
        self.assertEqual(len(posts), 0)

    def test_add_comment(self):
        post = Post.objects.last()
        form_data = {
            'text': 'test comment',
            'post': post,
            'author': self.authorized_client,
        }
        response_post = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': post.id}),
            data=form_data,
            follow=False,
        )
        self.assertEqual(response_post.status_code, 302)

        response_get = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': post.id}),
        )
        self.assertEqual(len(response_get.context['comments']), 1)

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


class FollowCommentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        UserModel.objects.create(username='auth', )
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            description='Тестовое описание',
            slug='test-slug')
        cls.follower = UserModel.objects.create(
            username='follower',
        )
        cls.next_follower = UserModel.objects.create_user(
            username='next_follower',
        )
        cls.following = UserModel.objects.create_user(
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
        follower = FollowCommentTests.follower
        next_follower = FollowCommentTests.next_follower
        following = FollowCommentTests.following
        self.follower_client = Client()
        self.follower_client.force_login(follower)
        self.next_follower_client = Client()
        self.next_follower_client.force_login(next_follower)
        self.following_client = Client()
        self.following_client.force_login(following)
        self.guest_user_client = Client()

    def test_follow(self):
        self.follower_client.get(
            reverse('posts:profile_follow',
            kwargs={'username': FollowCommentTests.following})
            )
        self.assertEqual(Follow.objects.count(), 1)

    def test_unfollow(self):
        self.follower_client.get(
            reverse('posts:profile_unfollow',
            kwargs={'username': FollowCommentTests.following})
            )
        self.assertEqual(Follow.objects.count(), 0)

    def test_follow_page(self):
        self.follower_client.get(
            reverse('posts:profile_follow',
            kwargs={'username': FollowCommentTests.following})
            )
        self.assertEqual(Follow.objects.count(), 1)
        form_data_for_follow_page = {
            'text': 'Пост для подписчика'
        }
        self.following_client.post(
            reverse('posts:post_create'
            ),
            data=form_data_for_follow_page,
            follow=True
        )
        response = self.follower_client.get(reverse('posts:follow_index'))
        self.assertContains(response, 'Пост для подписчика')
        response = self.next_follower_client.get(reverse('posts:follow_index'))
        self.assertNotContains(response, 'Пост для подписчика')
     