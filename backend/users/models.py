"""Модели пользователей."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator

from core.constants import (
    MAX_EMAIL_LENGTH,
    MAX_USERNAME_LENGTH,
    MAX_NAME_LENGTH,
)


class User(AbstractUser):
    """Кастомная модель пользователя."""

    email = models.EmailField(
        'Email',
        max_length=MAX_EMAIL_LENGTH,
        unique=True,
    )
    username = models.CharField(
        'Имя пользователя',
        max_length=MAX_USERNAME_LENGTH,
        unique=True,
        validators=[RegexValidator(
            regex=r'^[\w.@+-]+$',
            message='Enter a valid username',
            code='invalid_name',
        )],
    )
    first_name = models.CharField(
        'Имя',
        max_length=MAX_NAME_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=MAX_NAME_LENGTH,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users/avatars/',
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['email']

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """Модель подписок пользователей."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='prevent_self_subscription'
            ),
        ]

    def __str__(self):
        return f'{self.user} подписан на {self.author}'
