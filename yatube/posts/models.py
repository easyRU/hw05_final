from django.contrib.auth import get_user_model
from django.db import models

UserModel = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200,
                             verbose_name='Группа')
    slug = models.SlugField(unique=True)
    description = models.TextField(verbose_name='Группа')

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def __str__(self) -> str:
        return self.title


class Post(models.Model):
    text = models.TextField(verbose_name='Текст поста',
                            help_text='Введите текст поста')
    pub_date = models.DateTimeField(auto_now_add=True,
                                    verbose_name='Дата публикации',
                                    help_text='Дата публикации')

    author = models.ForeignKey(
        UserModel,
        verbose_name='Автор',
        help_text='Автор поста',
        on_delete=models.CASCADE,
        related_name='posts'
    )

    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        help_text='Группа, к которой будет относиться пост',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='posts'
    )

    image = models.ImageField(
        'Картинка',
        upload_to='posts/',
        blank=True
    )

    class Meta:
        verbose_name = "Пост"
        verbose_name_plural = 'Посты'
        ordering = ('-pub_date', )

    def __str__(self) -> str:
        return self.text[:15]


class Comment(models.Model):
    text = models.TextField(
        'Текст комментария',
        help_text='Напишите комментарий'
    )
    created = models.DateTimeField(
        'Дата комментария',
        auto_now_add=True
    )
    author = models.ForeignKey(
        UserModel,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост'
    )

    class Meta:
        verbose_name = 'Комментарии'

    def __str__(self):
        return self.text[:15]


class Follow(models.Model):
    user = models.ForeignKey(
        UserModel, on_delete=models.CASCADE,
        related_name='follower', verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        UserModel, on_delete=models.CASCADE,
        related_name='following', verbose_name='На кого подписываемся'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'], name='unique_follow'
            )
        ]
