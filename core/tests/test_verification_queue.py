from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Listing, ListingOutdatedReport


class VerificationQueueTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            email='staff-queue@example.com',
            password='password123',
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            email='normal-queue@example.com',
            password='password123',
            is_staff=False,
        )

        self.stale_listing = Listing.objects.create(
            title='Stale Soccer',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='League A',
            city_town='Attleboro',
            location_name='Field A',
            age_min=8,
            age_max=12,
            season_or_dates='Spring',
            registration_url='https://example.com/stale',
            description='Old verification',
            last_verified_at=timezone.now() - timedelta(days=120),
            status=Listing.Status.PUBLISHED,
        )
        self.fresh_listing = Listing.objects.create(
            title='Fresh Soccer',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='League B',
            city_town='Mansfield',
            location_name='Field B',
            age_min=8,
            age_max=12,
            season_or_dates='Spring',
            registration_url='https://example.com/fresh',
            description='Recent verification',
            last_verified_at=timezone.now() - timedelta(days=10),
            status=Listing.Status.PUBLISHED,
        )
        self.report = ListingOutdatedReport.objects.create(
            listing=self.fresh_listing,
            reporter_email='parent@example.com',
            notes='Dates look outdated.',
        )

    def test_verification_queue_requires_staff(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('core:verification_queue'))
        self.assertEqual(response.status_code, 403)

    def test_verification_queue_shows_stale_and_open_reports(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('core:verification_queue'))
        self.assertEqual(response.status_code, 200)

        stale_ids = [listing.id for listing in response.context['stale_listings']]
        open_ids = [report.id for report in response.context['open_reports']]

        self.assertIn(self.stale_listing.id, stale_ids)
        self.assertNotIn(self.fresh_listing.id, stale_ids)
        self.assertIn(self.report.id, open_ids)

    def test_verification_queue_can_resolve_report(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:verification_queue'),
            data={'action': 'resolve', 'report_id': self.report.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertTrue(self.report.resolved)

    def test_verification_queue_can_publish_draft_listing(self):
        draft_listing = Listing.objects.create(
            title='Draft Soccer',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Draft Org',
            city_town='Attleboro',
            location_name='Draft Field',
            age_min=7,
            age_max=10,
            season_or_dates='Spring',
            registration_url='https://example.com/draft',
            description='Draft listing',
            status=Listing.Status.DRAFT,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:verification_queue'),
            data={'action': 'publish', 'listing_id': draft_listing.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        draft_listing.refresh_from_db()
        self.assertEqual(draft_listing.status, Listing.Status.PUBLISHED)

    def test_verification_queue_can_mark_listing_verified_today(self):
        old_verified_at = self.stale_listing.last_verified_at
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:verification_queue'),
            data={'action': 'verify', 'listing_id': self.stale_listing.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.stale_listing.refresh_from_db()
        self.assertGreater(self.stale_listing.last_verified_at, old_verified_at)

    def test_verification_queue_filters_by_town_and_sport(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(
            reverse('core:verification_queue'),
            {'town': 'Attleboro', 'sport': 'Soccer'},
        )
        self.assertEqual(response.status_code, 200)
        stale_ids = [listing.id for listing in response.context['stale_listings']]
        self.assertIn(self.stale_listing.id, stale_ids)
        self.assertNotIn(self.fresh_listing.id, stale_ids)

    def test_verification_queue_has_reports_filter(self):
        draft_without_report = Listing.objects.create(
            title='Draft No Report',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Draft Org 2',
            city_town='Attleboro',
            location_name='Field C',
            age_min=7,
            age_max=10,
            season_or_dates='Spring',
            registration_url='https://example.com/draft-no-report',
            description='No report',
            status=Listing.Status.DRAFT,
        )
        draft_with_report = Listing.objects.create(
            title='Draft With Report',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Draft Org 3',
            city_town='Attleboro',
            location_name='Field D',
            age_min=7,
            age_max=10,
            season_or_dates='Spring',
            registration_url='https://example.com/draft-with-report',
            description='With report',
            status=Listing.Status.DRAFT,
        )
        ListingOutdatedReport.objects.create(
            listing=draft_with_report,
            notes='Needs update',
        )
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('core:verification_queue'), {'has_reports': '1'})
        self.assertEqual(response.status_code, 200)
        draft_ids = [listing.id for listing in response.context['draft_listings']]
        self.assertIn(draft_with_report.id, draft_ids)
        self.assertNotIn(draft_without_report.id, draft_ids)

    def test_verification_queue_includes_summary_snapshot(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('core:verification_queue'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('queue_summary', response.context)
        self.assertIn('queue_snapshot_generated_at', response.context)
        self.assertGreaterEqual(response.context['queue_summary']['stale_count'], 1)
        self.assertGreaterEqual(response.context['queue_summary']['open_report_count'], 1)
