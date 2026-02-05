"""Модели рецептов."""

import random
import string

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from users.models import User
from core.constants import (
    MAX_TAG_NAME_LENGTH,
    MAX_TAG_SLUG_LENGTH,
    MAX_INGREDIENT_NAME_LENGTH,
    MAX_MEASUREMENT_UNIT_LENGTH,
    MAX_RECIPE_NAME_LENGTH,
    MIN_COOKING_TIME,
    MAX_COOKING_TIME,
    MIN_INGREDIENT_AMOUNT,
    MAX_INGREDIENT_AMOUNT,
    SHORT_LINK_LENGTH,
)


class Tag(models.Model):
    """Модель тегов."""

    name = models.CharField(
        'Название',
        max_length=MAX_TAG_NAME_LENGTH,
        unique=True,
    )
    slug = models.SlugField(
        'Слаг',
        max_length=MAX_TAG_SLUG_LENGTH,
        unique=True,
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'
        ordering = ['name']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """Модель ингредиентов (справочник)."""

    name = models.CharField(
        'Название',
        max_length=MAX_INGREDIENT_NAME_LENGTH,
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=MAX_MEASUREMENT_UNIT_LENGTH,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.name}, {self.measurement_unit}'


class Recipe(models.Model):
    """Модель рецептов."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
    )
    name = models.CharField(
        'Название',
        max_length=MAX_RECIPE_NAME_LENGTH,
    )
    image = models.ImageField(
        'Изображение',
        upload_to='recipes/images/',
    )
    text = models.TextField('Описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты',
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления (мин)',
        validators=[
            MinValueValidator(MIN_COOKING_TIME),
            MaxValueValidator(MAX_COOKING_TIME),
        ],
    )
    short_link = models.CharField(
        'Короткая ссылка',
        max_length=SHORT_LINK_LENGTH,
        unique=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True,
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created_at']
        default_related_name = 'recipes'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.short_link:
            self.short_link = self._generate_short_link()
        super().save(*args, **kwargs)

    def _generate_short_link(self):
        """Генерация уникальной короткой ссылки."""
        chars = string.ascii_letters + string.digits
        while True:
            link = ''.join(random.choices(chars, k=SHORT_LINK_LENGTH))
            if not Recipe.objects.filter(short_link=link).exists():
                return link


class RecipeIngredient(models.Model):
    """Промежуточная модель ингредиентов в рецепте."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт',
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes',
        verbose_name='Ингредиент',
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=[
            MinValueValidator(MIN_INGREDIENT_AMOUNT),
            MaxValueValidator(MAX_INGREDIENT_AMOUNT),
        ],
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.ingredient.name} в {self.recipe.name}'


class UserRecipeBase(models.Model):
    """Абстрактная базовая модель для связи пользователя и рецепта."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_%(class)ss',
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='%(class)s_unique_user_recipe'
            )
        ]


class Favorite(UserRecipeBase):
    """Модель избранных рецептов."""

    class Meta(UserRecipeBase.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в избранное'


class ShoppingCart(UserRecipeBase):
    """Модель списка покупок."""

    class Meta(UserRecipeBase.Meta):
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в корзину'
