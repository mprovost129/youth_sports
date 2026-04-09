import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from core.models import Listing


class ImportListingsCommandTests(TestCase):
    def _write_csv(self, rows):
        headers = [
            'title',
            'category',
            'subtype',
            'organization_name',
            'city_town',
            'location_name',
            'address',
            'age_min',
            'age_max',
            'gender',
            'season_or_dates',
            'start_date',
            'end_date',
            'registration_url',
            'cost',
            'description',
            'last_verified_at',
            'status',
        ]
        temp = tempfile.NamedTemporaryFile(mode='w', newline='', suffix='.csv', delete=False, encoding='utf-8')
        try:
            writer = csv.DictWriter(temp, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
            temp.close()
            return Path(temp.name)
        except Exception:
            temp.close()
            Path(temp.name).unlink(missing_ok=True)
            raise

    def test_import_creates_records(self):
        csv_path = self._write_csv(
            [
                {
                    'title': 'Attleboro Youth Soccer U10',
                    'category': 'sport',
                    'subtype': 'Soccer',
                    'organization_name': 'Attleboro Youth Soccer',
                    'city_town': 'Attleboro',
                    'location_name': 'Community Field',
                    'address': '123 Main St',
                    'age_min': '8',
                    'age_max': '10',
                    'gender': 'coed',
                    'season_or_dates': 'Spring',
                    'start_date': '2026-04-20',
                    'end_date': '2026-06-20',
                    'registration_url': 'https://example.com/soccer',
                    'cost': '$125',
                    'description': 'Recreational youth soccer',
                    'last_verified_at': '',
                    'status': 'active',
                }
            ]
        )
        output = StringIO()
        try:
            call_command('import_listings', str(csv_path), stdout=output)
        finally:
            csv_path.unlink(missing_ok=True)

        self.assertEqual(Listing.objects.count(), 1)
        self.assertIn('created=1', output.getvalue())
        self.assertIn('errors=0', output.getvalue())

    def test_dry_run_does_not_persist(self):
        csv_path = self._write_csv(
            [
                {
                    'title': 'Robotics Club',
                    'category': 'activity',
                    'subtype': 'Robotics',
                    'organization_name': 'STEM Hub',
                    'city_town': 'Attleboro',
                    'location_name': 'Library',
                    'address': '',
                    'age_min': '9',
                    'age_max': '13',
                    'gender': 'coed',
                    'season_or_dates': 'Fall',
                    'start_date': '',
                    'end_date': '',
                    'registration_url': 'https://example.com/robotics',
                    'cost': '',
                    'description': 'Hands-on robotics',
                    'last_verified_at': '',
                    'status': 'active',
                }
            ]
        )
        output = StringIO()
        try:
            call_command('import_listings', str(csv_path), '--dry-run', stdout=output)
        finally:
            csv_path.unlink(missing_ok=True)

        self.assertEqual(Listing.objects.count(), 0)
        self.assertIn('dry_run=True', output.getvalue())
        self.assertIn('created=1', output.getvalue())

    def test_update_existing_updates_matching_listing(self):
        listing = Listing.objects.create(
            title='Attleboro Youth Soccer U10',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Attleboro Youth Soccer',
            city_town='Attleboro',
            location_name='Old Field',
            age_min=8,
            age_max=10,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/old',
            description='Old description',
        )
        csv_path = self._write_csv(
            [
                {
                    'title': listing.title,
                    'category': 'sport',
                    'subtype': 'Soccer',
                    'organization_name': listing.organization_name,
                    'city_town': listing.city_town,
                    'location_name': 'New Field',
                    'address': '',
                    'age_min': '8',
                    'age_max': '10',
                    'gender': 'coed',
                    'season_or_dates': 'Spring 2026',
                    'start_date': '2026-04-20',
                    'end_date': '',
                    'registration_url': 'https://example.com/new',
                    'cost': '',
                    'description': 'Updated description',
                    'last_verified_at': '',
                    'status': 'active',
                }
            ]
        )
        output = StringIO()
        try:
            call_command('import_listings', str(csv_path), '--update-existing', stdout=output)
        finally:
            csv_path.unlink(missing_ok=True)

        listing.refresh_from_db()
        self.assertEqual(Listing.objects.count(), 1)
        self.assertEqual(listing.location_name, 'New Field')
        self.assertEqual(listing.registration_url, 'https://example.com/new')
        self.assertIn('updated=1', output.getvalue())
