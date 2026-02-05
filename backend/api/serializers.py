"""Сериализаторы API."""

from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserSerializer as DjoserUserSerializer
from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer,
)
from rest_framework import serializers

from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
)
from users.models import Subscription
from .fields import Base64ImageField

User = get_user_model()


# ========== USER SERIALIZERS ==========

class AvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для аватара."""

    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(DjoserUserSerializer):
    """Сериализатор пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        )

    def get_is_subscribed(self, obj):
        """Проверка подписки текущего пользователя на автора."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(
                user=request.user, author=obj
            ).exists()
        )


class UserCreateSerializer(DjoserUserCreateSerializer):
    """Сериализатор создания пользователя."""

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )


# ========== TAG SERIALIZERS ==========

class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов."""

    class Meta:
        model = Tag
        fields = '__all__'


# ========== INGREDIENT SERIALIZERS ==========

class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов."""

    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов в рецепте (для чтения)."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientInRecipeWriteSerializer(serializers.Serializer):
    """Сериализатор ингредиентов для записи рецепта."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=1, max_value=32000)


# ========== RECIPE SERIALIZERS ==========

class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Сокращенный сериализатор рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserRecipeBaseSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для избранного и корзины."""

    class Meta:
        fields = ('user', 'recipe')
        read_only_fields = ('user',)

    def validate(self, data):
        """Валидация: проверка на дубликат."""
        user = self.context['request'].user
        recipe = data['recipe']
        if self.Meta.model.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                {'errors': 'Рецепт уже добавлен'}
            )
        return data

    def create(self, validated_data):
        """Создание записи."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        """Возврат данных рецепта."""
        return RecipeMinifiedSerializer(instance.recipe).data


class FavoriteSerializer(UserRecipeBaseSerializer):
    """Сериализатор избранного."""

    class Meta(UserRecipeBaseSerializer.Meta):
        model = Favorite


class ShoppingCartSerializer(UserRecipeBaseSerializer):
    """Сериализатор корзины."""

    class Meta(UserRecipeBaseSerializer.Meta):
        model = ShoppingCart


class RecipeReadSerializer(serializers.ModelSerializer):
    """Сериализатор рецепта для чтения."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def get_is_favorited(self, obj):
        """Проверка добавления в избранное."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and obj.in_favorites.filter(user=request.user).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Проверка добавления в корзину."""
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and obj.in_shoppingcarts.filter(user=request.user).exists()
        )


class RecipeWriteSerializer(serializers.ModelSerializer):
    """Сериализатор рецепта для создания/обновления."""

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = IngredientInRecipeWriteSerializer(many=True)
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'ingredients',
            'tags',
            'image',
            'name',
            'text',
            'cooking_time',
        )

    def validate(self, data):
        """Валидация данных рецепта."""
        ingredients = data.get('ingredients')
        tags = data.get('tags')

        if not ingredients:
            raise serializers.ValidationError(
                {'ingredients': 'Нужен хотя бы один ингредиент'}
            )
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужен хотя бы один тег'}
            )

        ingredient_ids = [item['id'].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                {'ingredients': 'Ингредиенты не должны повторяться'}
            )

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги не должны повторяться'}
            )

        return data

    @staticmethod
    def _create_ingredients(recipe, ingredients):
        """Создание связей ингредиентов с рецептом."""
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['id'],
                amount=item['amount'],
            )
            for item in ingredients
        ])

    @transaction.atomic
    def create(self, validated_data):
        """Создание рецепта."""
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(
            author=self.context['request'].user,
            **validated_data,
        )
        recipe.tags.set(tags)
        self._create_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        """Обновление рецепта."""
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')

        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.recipe_ingredients.all().delete()
        self._create_ingredients(instance, ingredients)

        return instance

    def to_representation(self, instance):
        """Возврат данных через сериализатор для чтения."""
        return RecipeReadSerializer(instance, context=self.context).data


class ShortLinkSerializer(serializers.Serializer):
    """Сериализатор короткой ссылки."""

    short_link = serializers.SerializerMethodField()

    def get_short_link(self, obj):
        """Генерация абсолютной короткой ссылки."""
        request = self.context.get('request')
        return request.build_absolute_uri(f'/s/{obj.short_link}/')

    def to_representation(self, instance):
        """Переименовываем short_link в short-link."""
        data = super().to_representation(instance)
        data['short-link'] = data.pop('short_link')
        return data


# ========== SUBSCRIPTION SERIALIZERS ==========

class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписки."""

    class Meta:
        model = Subscription
        fields = ('user', 'author')
        read_only_fields = ('user',)

    def validate(self, data):
        """Валидация подписки."""
        user = self.context['request'].user
        author = data['author']

        if user == author:
            raise serializers.ValidationError(
                {'errors': 'Нельзя подписаться на себя'}
            )
        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                {'errors': 'Вы уже подписаны'}
            )
        return data

    def create(self, validated_data):
        """Создание подписки."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserWithRecipesSerializer(UserSerializer):
    """Сериализатор пользователя с рецептами."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        """Получение рецептов пользователя с лимитом."""
        request = self.context.get('request')
        recipes = obj.recipes.all()
        if request:
            recipes_limit = request.query_params.get('recipes_limit')
            if recipes_limit and recipes_limit.isdigit():
                recipes = recipes[:int(recipes_limit)]
        return RecipeMinifiedSerializer(recipes, many=True).data
