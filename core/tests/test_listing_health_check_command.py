import json
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from core.models import Listing, ListingOutdatedReport, ListingSuggestion


class ListingHealthCheckCommandTests(TestCase):
    def test_json_output_includes_expected_counts(self):
        stale_listing = Listing.objects.create(
            title='Stale Soccer',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Org',
            city_town='Attleboro',
            location_name='Field',
            age_min=8,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/stale',
            description='Stale listing',
            status=Listing.Status.PUBLISHED,
            last_verified_at=timezone.now() - timedelta(days=100),
        )
        ListingOutdatedReport.objects.create(
            listing=stale_listing,
            notes='Needs review',
        )
        Listing.objects.create(
            title='Old Draft',
            category=Listing.Category.ACTIVITY,
            subtype='Robotics',
            organization_name='Org',
            city_town='Attleboro',
            location_name='Lab',
            age_min=9,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Fall',
            registration_url='https://example.com/draft',
            description='Old draft',
            status=Listing.Status.DRAFT,
            last_verified_at=timezone.now() - timedelta(days=2),
        )
        Listing.objects.filter(title='Old Draft').update(
            updated_at=timezone.now() - timedelta(days=20)
        )
        ListingSuggestion.objects.create(
            title='Pending Suggestion',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Org',
            city_town='Attleboro',
            location_name='Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/suggestion',
            description='Suggestion',
            status=ListingSuggestion.Status.PENDING,
        )
        ListingSuggestion.objects.filter(title='Pending Suggestion').update(
            created_at=timezone.now() - timedelta(days=30)
        )

        out = StringIO()
        call_command('listing_health_check', '--json', stdout=out)
        payload = json.loads(out.getvalue())

        self.assertTrue(payload['has_alerts'])
        self.assertEqual(payload['counts']['stale_published'], 1)
        self.assertEqual(payload['counts']['unresolved_reports'], 1)
        self.assertEqual(payload['counts']['old_drafts'], 1)
        self.assertEqual(payload['counts']['old_pending_suggestions'], 1)

    def test_fail_on_alert_raises_command_error(self):
        Listing.objects.create(
            title='Stale Soccer',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Org',
            city_town='Attleboro',
            location_name='Field',
            age_min=8,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/stale',
            description='Stale listing',
            status=Listing.Status.PUBLISHED,
            last_verified_at=timezone.now() - timedelta(days=120),
        )

        with self.assertRaises(CommandError):
            call_command('listing_health_check', '--fail-on-alert')

    def test_send_email_sends_alert_when_configured(self):
        Listing.objects.create(
            title='Stale Soccer',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Org',
            city_town='Attleboro',
            location_name='Field',
            age_min=8,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/stale',
            description='Stale listing',
            status=Listing.Status.PUBLISHED,
            last_verified_at=timezone.now() - timedelta(days=120),
        )
        with patch.dict('os.environ', {'OPS_ALERT_EMAIL': 'ops@example.com'}):
            call_command('listing_health_check', '--send-email')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ops@example.com'])
