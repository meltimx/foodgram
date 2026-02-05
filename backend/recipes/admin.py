"""Админка рецептов."""

from django.contrib import admin

from .models import (
    Tag,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админка тегов."""

    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Админка ингредиентов."""

    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


class RecipeIngredientInline(admin.TabularInline):
    """Инлайн ингредиентов в рецепте."""

    model = RecipeIngredient
    extra = 1
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Админка рецептов."""

    list_display = (
        'id',
        'name',
        'author',
        'cooking_time',
        'favorites_count',
        'created_at',
    )
    list_filter = ('tags', 'author')
    search_fields = ('name', 'author__username')
    readonly_fields = ('favorites_count', 'short_link')
    filter_horizontal = ('tags',)
    inlines = [RecipeIngredientInline]

    @admin.display(description='В избранном')
    def favorites_count(self, obj):
        """Количество добавлений в избранное."""
        return obj.in_favorites.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Админка избранного."""

    list_display = ('id', 'user', 'recipe')
    list_filter = ('user',)
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    """Админка списка покупок."""

    list_display = ('id', 'user', 'recipe')
    list_filter = ('user',)
    search_fields = ('user__username', 'recipe__name')
