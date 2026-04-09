import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from core.models import Listing


class Command(BaseCommand):
    help = 'Import Listing records from a CSV file.'

    required_columns = [
        'title',
        'category',
        'subtype',
        'organization_name',
        'city_town',
        'location_name',
        'age_min',
        'age_max',
        'season_or_dates',
        'registration_url',
        'description',
    ]

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to CSV file to import.')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and parse rows but do not write any data.',
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing listing matched by title + organization_name + city_town.',
        )

    def handle(self, *args, **options):
        csv_path = Path(options['csv_path']).expanduser().resolve()
        dry_run = options['dry_run']
        update_existing = options['update_existing']

        if not csv_path.exists():
            raise CommandError(f'CSV file not found: {csv_path}')

        with csv_path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise CommandError('CSV has no header row.')

            missing = [name for name in self.required_columns if name not in reader.fieldnames]
            if missing:
                raise CommandError(f'Missing required columns: {", ".join(missing)}')

            stats = {
                'created': 0,
                'updated': 0,
                'skipped': 0,
                'errors': 0,
            }

            row_errors = []

            with transaction.atomic():
                for line_number, row in enumerate(reader, start=2):
                    try:
                        cleaned = self._clean_row(row, line_number)
                        self._upsert(cleaned, update_existing, stats)
                    except Exception as exc:
                        stats['errors'] += 1
                        row_errors.append(f'Line {line_number}: {exc}')

                if dry_run:
                    transaction.set_rollback(True)

            self.stdout.write(
                self.style.SUCCESS(
                    f'Import complete (dry_run={dry_run}): '
                    f'created={stats["created"]}, updated={stats["updated"]}, '
                    f'skipped={stats["skipped"]}, errors={stats["errors"]}'
                )
            )

            for err in row_errors[:20]:
                self.stdout.write(self.style.WARNING(err))
            if len(row_errors) > 20:
                self.stdout.write(self.style.WARNING(f'...and {len(row_errors) - 20} more errors'))

    def _upsert(self, cleaned, update_existing, stats):
        lookup = {
            'title': cleaned['title'],
            'organization_name': cleaned['organization_name'],
            'city_town': cleaned['city_town'],
        }

        existing = Listing.objects.filter(**lookup).first()
        if existing and not update_existing:
            stats['skipped'] += 1
            return

        if existing and update_existing:
            for field, value in cleaned.items():
                setattr(existing, field, value)
            existing.save()
            stats['updated'] += 1
            return

        Listing.objects.create(**cleaned)
        stats['created'] += 1

    def _clean_row(self, row, line_number):
        category = self._normalize_choice(
            row.get('category', ''),
            Listing.Category.choices,
            'category',
            line_number,
        )
        gender = self._normalize_choice(
            row.get('gender', '') or Listing.Gender.NOT_SPECIFIED,
            Listing.Gender.choices,
            'gender',
            line_number,
        )
        status = self._normalize_choice(
            row.get('status', '') or Listing.Status.DRAFT,
            Listing.Status.choices,
            'status',
            line_number,
        )

        age_min = self._parse_int(row.get('age_min', ''), 'age_min', line_number)
        age_max = self._parse_int(row.get('age_max', ''), 'age_max', line_number)

        cleaned = {
            'title': self._required_text(row, 'title', line_number),
            'category': category,
            'subtype': self._required_text(row, 'subtype', line_number),
            'organization_name': self._required_text(row, 'organization_name', line_number),
            'city_town': self._required_text(row, 'city_town', line_number),
            'location_name': self._required_text(row, 'location_name', line_number),
            'address': (row.get('address') or '').strip(),
            'age_min': age_min,
            'age_max': age_max,
            'gender': gender,
            'season_or_dates': self._required_text(row, 'season_or_dates', line_number),
            'start_date': self._parse_optional_date(row.get('start_date', ''), 'start_date', line_number),
            'end_date': self._parse_optional_date(row.get('end_date', ''), 'end_date', line_number),
            'registration_url': self._required_text(row, 'registration_url', line_number),
            'cost': (row.get('cost') or '').strip(),
            'description': self._required_text(row, 'description', line_number),
            'last_verified_at': self._parse_optional_datetime(
                row.get('last_verified_at', ''),
                'last_verified_at',
                line_number,
            )
            or timezone.now(),
            'status': status,
        }

        return cleaned

    def _required_text(self, row, field, line_number):
        value = (row.get(field) or '').strip()
        if not value:
            raise CommandError(f'{field} is required (line {line_number}).')
        return value

    def _parse_int(self, raw_value, field, line_number):
        value = (raw_value or '').strip()
        if not value:
            raise CommandError(f'{field} is required (line {line_number}).')
        try:
            return int(value)
        except ValueError as exc:
            raise CommandError(f'{field} must be an integer (line {line_number}).') from exc

    def _parse_optional_date(self, raw_value, field, line_number):
        value = (raw_value or '').strip()
        if not value:
            return None
        parsed = parse_date(value)
        if parsed is None:
            raise CommandError(f'{field} must be YYYY-MM-DD (line {line_number}).')
        return parsed

    def _parse_optional_datetime(self, raw_value, field, line_number):
        value = (raw_value or '').strip()
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed is None:
            raise CommandError(f'{field} must be ISO datetime (line {line_number}).')
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def _normalize_choice(self, raw_value, choices, field, line_number):
        value = (raw_value or '').strip()
        if field == 'status':
            legacy = {
                'active': Listing.Status.PUBLISHED,
                'inactive': Listing.Status.ARCHIVED,
            }
            if value.lower() in legacy:
                value = legacy[value.lower()]
        lookup = {}
        for db_value, label in choices:
            lookup[db_value.lower()] = db_value
            lookup[str(label).lower()] = db_value

        normalized = lookup.get(value.lower())
        if normalized is None:
            allowed = ', '.join(sorted({key for key in lookup.keys()}))
            raise CommandError(
                f'{field} has invalid value "{value}" (line {line_number}). '
                f'Allowed: {allowed}'
            )
        return normalized
