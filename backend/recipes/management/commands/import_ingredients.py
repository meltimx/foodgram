"""Команда импорта ингредиентов."""

import csv
import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    """Импорт ингредиентов из JSON или CSV файла."""

    help = 'Импорт ингредиентов из JSON или CSV файла'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Путь к файлу')

    def handle(self, *args, **options):
        file_path = options['file_path']

        if file_path.endswith('.json'):
            self._import_from_json(file_path)
        elif file_path.endswith('.csv'):
            self._import_from_csv(file_path)
        else:
            self.stdout.write(
                self.style.ERROR('Неподдерживаемый формат файла')
            )

    def _import_from_json(self, file_path):
        """Импорт из JSON."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        ingredients = [
            Ingredient(
                name=item['name'],
                measurement_unit=item['measurement_unit']
            )
            for item in data
        ]
        Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(f'Импортировано {len(ingredients)} ингредиентов')
        )

    def _import_from_csv(self, file_path):
        """Импорт из CSV."""
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            ingredients = [
                Ingredient(name=row[0], measurement_unit=row[1])
                for row in reader
            ]
        Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)
        self.stdout.write(
            self.style.SUCCESS(f'Импортировано {len(ingredients)} ингредиентов')
        )
