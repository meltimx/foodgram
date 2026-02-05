"""ViewSets API."""

from datetime import datetime
from io import BytesIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import FileResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response

from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    RecipeIngredient,
    Favorite,
    ShoppingCart,
)
from users.models import Subscription
from .filters import IngredientFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    TagSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    ShortLinkSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
    SubscriptionSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer,
    AvatarSerializer,
)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    """ViewSet пользователей."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        """Получение текущего пользователя."""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar',
    )
    def avatar(self, request):
        """Обновление аватара."""
        serializer = AvatarSerializer(
            request.user,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаление аватара."""
        request.user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
    )
    def subscriptions(self, request):
        """Получение списка подписок."""
        subscriptions = User.objects.filter(
            subscribers__user=request.user
        ).annotate(recipes_count=Count('recipes'))
        page = self.paginate_queryset(subscriptions)
        serializer = UserWithRecipesSerializer(
            page,
            many=True,
            context={'request': request},
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
    )
    def subscribe(self, request, id=None):
        """Подписка/отписка от пользователя."""
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data={'author': author.id},
                context={'request': request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            author = User.objects.annotate(
                recipes_count=Count('recipes')
            ).get(id=id)
            return Response(
                UserWithRecipesSerializer(
                    author, context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED,
            )

        # DELETE
        deleted, _ = Subscription.objects.filter(
            user=request.user,
            author=author,
        ).delete()
        return Response(
            None if deleted else {'errors': 'Вы не были подписаны'},
            status=(status.HTTP_204_NO_CONTENT if deleted
                    else status.HTTP_400_BAD_REQUEST),
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet тегов (только чтение)."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet ингредиентов (только чтение)."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """ViewSet рецептов."""

    queryset = Recipe.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия."""
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        """Получение короткой ссылки на рецепт."""
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = ShortLinkSerializer(recipe, context={'request': request})
        return Response(serializer.data)

    def _add_to(self, serializer_class, request, pk):
        """Добавление рецепта в модель (избранное/корзина)."""
        serializer = serializer_class(
            data={'recipe': pk},
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _remove_from(self, model, request, pk):
        """Удаление рецепта из модели (избранное/корзина)."""
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = model.objects.filter(
            user=request.user,
            recipe=recipe,
        ).delete()
        if not deleted:
            return Response(
                {'errors': 'Рецепт не был добавлен'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        """Добавление/удаление из избранного."""
        if request.method == 'POST':
            return self._add_to(FavoriteSerializer, request, pk)
        return self._remove_from(Favorite, request, pk)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart',
    )
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление из корзины."""
        if request.method == 'POST':
            return self._add_to(ShoppingCartSerializer, request, pk)
        return self._remove_from(ShoppingCart, request, pk)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        """Скачивание списка покупок в PDF."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__in_shoppingcarts__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit',
        ).annotate(total_amount=Sum('amount'))

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        fonts_dir = Path(__file__).parent / 'fonts'
        font_path = fonts_dir / 'DejaVuSans.ttf'
        font_path_bold = fonts_dir / 'DejaVuSans-Bold.ttf'
        pdfmetrics.registerFont(TTFont('DejaVuSans', str(font_path)))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', str(font_path_bold)))

        # Заголовок с фоном
        pdf.setFillColor(colors.HexColor('#4A90D9'))
        pdf.rect(0, height - 80, width, 80, fill=True, stroke=False)
        pdf.setFillColor(colors.white)
        pdf.setFont('DejaVuSans-Bold', 28)
        pdf.drawCentredString(width / 2, height - 55, 'Список покупок')

        # Дата и пользователь
        pdf.setFillColor(colors.HexColor('#666666'))
        pdf.setFont('DejaVuSans', 10)
        date_str = datetime.now().strftime('%d.%m.%Y')
        pdf.drawString(50, height - 110, f'Дата: {date_str}')
        username = request.user.username
        pdf.drawString(50, height - 125, f'Пользователь: {username}')

        # Разделительная линия
        pdf.setStrokeColor(colors.HexColor('#E0E0E0'))
        pdf.setLineWidth(1)
        pdf.line(50, height - 140, width - 50, height - 140)

        # Список ингредиентов
        y = height - 170
        row_height = 30
        pdf.setFont('DejaVuSans', 12)

        for i, item in enumerate(ingredients, 1):
            # Чередующийся фон строк
            if i % 2 == 0:
                pdf.setFillColor(colors.HexColor('#F5F5F5'))
                pdf.rect(
                    50, y - 5, width - 100, row_height, fill=True, stroke=False
                )

            # Номер
            pdf.setFillColor(colors.HexColor('#4A90D9'))
            pdf.setFont('DejaVuSans-Bold', 12)
            pdf.drawString(60, y + 5, f'{i}.')

            # Название ингредиента
            pdf.setFillColor(colors.HexColor('#333333'))
            pdf.setFont('DejaVuSans', 12)
            pdf.drawString(90, y + 5, item['ingredient__name'].capitalize())

            # Количество (справа)
            unit = item['ingredient__measurement_unit']
            amount_text = f"{item['total_amount']} {unit}"
            pdf.setFont('DejaVuSans-Bold', 12)
            pdf.drawRightString(width - 60, y + 5, amount_text)

            y -= row_height

            # Новая страница при необходимости
            if y < 80:
                # Футер на текущей странице
                pdf.setFillColor(colors.HexColor('#999999'))
                pdf.setFont('DejaVuSans', 9)
                footer = 'Foodgram — Продуктовый помощник'
                pdf.drawCentredString(width / 2, 30, footer)
                pdf.showPage()
                y = height - 50
                pdf.setFont('DejaVuSans', 12)

        # Итоговая линия
        pdf.setStrokeColor(colors.HexColor('#4A90D9'))
        pdf.setLineWidth(2)
        pdf.line(50, y, width - 50, y)

        # Итого
        pdf.setFillColor(colors.HexColor('#333333'))
        pdf.setFont('DejaVuSans-Bold', 14)
        pdf.drawString(60, y - 25, f'Всего позиций: {len(list(ingredients))}')

        # Футер
        pdf.setFillColor(colors.HexColor('#999999'))
        pdf.setFont('DejaVuSans', 9)
        pdf.drawCentredString(width / 2, 30, 'Foodgram — Продуктовый помощник')

        pdf.save()
        buffer.seek(0)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename='shopping_list.pdf',
        )


def short_link_redirect(request, short_link):
    """Редирект по короткой ссылке."""
    recipe = get_object_or_404(Recipe, short_link=short_link)
    return redirect(f'/recipes/{recipe.id}/')
