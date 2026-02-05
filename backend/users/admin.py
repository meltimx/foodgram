"""Админка пользователей."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Subscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка пользователей."""

    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
        'recipes_count',
        'subscribers_count',
        'is_staff',
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('id',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительно', {'fields': ('avatar',)}),
    )

    @admin.display(description='Рецепты')
    def recipes_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Подписчики')
    def subscribers_count(self, obj):
        return obj.subscribers.count()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Админка подписок."""

    list_display = ('id', 'user', 'author')
    list_filter = ('user', 'author')
    search_fields = ('user__username', 'author__username')
