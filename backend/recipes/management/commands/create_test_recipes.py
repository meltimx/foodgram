"""Команда создания тестовых рецептов."""

from django.core.management.base import BaseCommand

from recipes.models import Recipe, Tag, Ingredient, RecipeIngredient
from users.models import User


class Command(BaseCommand):
    """Создание тестовых рецептов для проверки пагинации."""

    help = 'Создание 10 тестовых рецептов'

    def handle(self, *args, **options):
        # Получаем или создаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={
                'email': 'test@test.com',
                'first_name': 'Test',
                'last_name': 'User',
            }
        )
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f'Создан пользователь: {user.username}')

        # Получаем или создаем теги
        tags_data = ['Завтрак', 'Обед', 'Ужин']
        tags = []
        for name in tags_data:
            tag, _ = Tag.objects.get_or_create(
                slug=name.lower(),
                defaults={'name': name}
            )
            tags.append(tag)

        # Получаем первые 5 ингредиентов
        ingredients = list(Ingredient.objects.all()[:5])
        if not ingredients:
            self.stdout.write(
                self.style.ERROR(
                    'Нет ингредиентов. Сначала импортируй: '
                    'python manage.py import_ingredients data/ingredients.json'
                )
            )
            return

        # Названия рецептов
        recipe_names = [
            'Тестовый рецепт 1',
            'Тестовый рецепт 2',
            'Тестовый рецепт 3',
            'Тестовый рецепт 4',
            'Тестовый рецепт 5',
            'Тестовый рецепт 6',
            'Тестовый рецепт 7',
            'Тестовый рецепт 8',
            'Тестовый рецепт 9',
            'Тестовый рецепт 10',
        ]

        created_count = 0
        for i, name in enumerate(recipe_names):
            recipe, created = Recipe.objects.get_or_create(
                name=name,
                author=user,
                defaults={
                    'text': f'Описание для {name}',
                    'cooking_time': 10 + i * 5,
                    'image': 'recipes/images/test.jpg',
                }
            )
            if created:
                # Добавляем теги (разные комбинации)
                recipe.tags.set(tags[:((i % 3) + 1)])
                # Добавляем ингредиенты
                for j, ingredient in enumerate(ingredients[:3]):
                    RecipeIngredient.objects.create(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=(j + 1) * 100
                    )
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Создано {created_count} тестовых рецептов')
        )
