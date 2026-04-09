from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Listing, ListingAnalyticsEvent, ListingOutdatedReport


class ListingModelTests(TestCase):
    def test_age_constraint_blocks_invalid_range(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Listing.objects.create(
                    title='Invalid Age Listing',
                    category=Listing.Category.SPORT,
                    subtype='Soccer',
                    organization_name='Sample Org',
                    city_town='Attleboro',
                    location_name='Field A',
                    age_min=12,
                    age_max=10,
                    gender=Listing.Gender.COED,
                    season_or_dates='Spring',
                    registration_url='https://example.com/register',
                    description='Invalid test record',
                )

    def test_date_constraint_blocks_end_before_start(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Listing.objects.create(
                    title='Invalid Date Listing',
                    category=Listing.Category.ACTIVITY,
                    subtype='Robotics',
                    organization_name='Sample Org',
                    city_town='Attleboro',
                    location_name='Center Hall',
                    age_min=8,
                    age_max=12,
                    gender=Listing.Gender.NOT_SPECIFIED,
                    season_or_dates='Summer',
                    start_date=date(2026, 7, 10),
                    end_date=date(2026, 7, 1),
                    registration_url='https://example.com/register',
                    description='Invalid date ordering',
                )

    def test_verification_properties_reflect_staleness(self):
        stale_listing = Listing.objects.create(
            title='Old Verification',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Sample Org',
            city_town='Attleboro',
            location_name='Field A',
            age_min=10,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/register',
            description='Old verification test',
            last_verified_at=timezone.now() - timedelta(days=120),
        )
        fresh_listing = Listing.objects.create(
            title='Fresh Verification',
            category=Listing.Category.SPORT,
            subtype='Basketball',
            organization_name='Sample Org',
            city_town='Attleboro',
            location_name='Gym A',
            age_min=10,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Winter',
            registration_url='https://example.com/register-fresh',
            description='Fresh verification test',
            last_verified_at=timezone.now() - timedelta(days=10),
        )

        self.assertTrue(stale_listing.is_stale)
        self.assertEqual(stale_listing.verification_label, 'Needs review')
        self.assertFalse(fresh_listing.is_stale)
        self.assertEqual(fresh_listing.verification_label, 'Verified recently')


class ListingViewTests(TestCase):
    def setUp(self):
        today = timezone.localdate()

        self.sports_future = Listing.objects.create(
            title='Future Soccer',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Attleboro Youth Soccer',
            city_town='Attleboro',
            location_name='Community Field',
            age_min=8,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            start_date=today + timedelta(days=7),
            end_date=today + timedelta(days=60),
            registration_url='https://example.com/soccer',
            description='Competitive soccer program',
            status=Listing.Status.PUBLISHED,
        )
        self.sports_no_date = Listing.objects.create(
            title='Basketball Skills',
            category=Listing.Category.SPORT,
            subtype='Basketball',
            organization_name='Skills Academy',
            city_town='North Attleborough',
            location_name='Gym 1',
            age_min=10,
            age_max=14,
            gender=Listing.Gender.BOYS,
            season_or_dates='Winter',
            registration_url='https://example.com/basketball',
            description='Skills training',
            status=Listing.Status.PUBLISHED,
        )
        self.activity_future = Listing.objects.create(
            title='STEM Robotics Club',
            category=Listing.Category.ACTIVITY,
            subtype='Robotics',
            organization_name='STEM Hub',
            city_town='Attleboro',
            location_name='Library Lab',
            age_min=9,
            age_max=13,
            gender=Listing.Gender.COED,
            season_or_dates='Fall',
            start_date=today + timedelta(days=14),
            end_date=today + timedelta(days=100),
            registration_url='https://example.com/robotics',
            description='Hands-on robotics',
            status=Listing.Status.PUBLISHED,
        )
        self.inactive_listing = Listing.objects.create(
            title='Inactive Program',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Old League',
            city_town='Attleboro',
            location_name='Old Field',
            age_min=7,
            age_max=11,
            gender=Listing.Gender.COED,
            season_or_dates='Past',
            registration_url='https://example.com/old',
            description='No longer active',
            status=Listing.Status.ARCHIVED,
        )

    def test_home_shows_upcoming_and_recent_active_only(self):
        response = self.client.get(reverse('core:home'))
        self.assertEqual(response.status_code, 200)

        upcoming = list(response.context['upcoming_listings'])
        recent = list(response.context['recent_listings'])

        self.assertIn(self.sports_future, upcoming)
        self.assertIn(self.sports_no_date, upcoming)
        self.assertNotIn(self.inactive_listing, upcoming)
        self.assertNotIn(self.inactive_listing, recent)

    def test_sports_page_filters_to_sport_category(self):
        response = self.client.get(reverse('core:sports'))
        self.assertEqual(response.status_code, 200)

        listings = list(response.context['listings'])
        self.assertIn(self.sports_future, listings)
        self.assertIn(self.sports_no_date, listings)
        self.assertNotIn(self.activity_future, listings)

    def test_activities_page_filters_by_age(self):
        response = self.client.get(reverse('core:activities'), {'age': '11'})
        self.assertEqual(response.status_code, 200)
        listings = list(response.context['listings'])
        self.assertIn(self.activity_future, listings)

        response = self.client.get(reverse('core:activities'), {'age': '15'})
        self.assertEqual(response.status_code, 200)
        listings = list(response.context['listings'])
        self.assertNotIn(self.activity_future, listings)

    def test_sports_page_filters_by_subtype_and_city(self):
        Listing.objects.create(
            title='Mansfield Baseball League',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Mansfield Youth Baseball',
            city_town='Mansfield',
            location_name='Baseball Complex',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/mansfield-baseball',
            description='Town baseball program',
            status=Listing.Status.PUBLISHED,
        )
        attleboro_baseball = Listing.objects.create(
            title='Attleboro Baseball League',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Attleboro Youth Baseball',
            city_town='Attleboro',
            location_name='Town Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/attleboro-baseball',
            description='Town baseball program',
            status=Listing.Status.PUBLISHED,
        )

        response = self.client.get(
            reverse('core:sports'),
            {'subtype': 'Baseball', 'city_town': 'Attleboro'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_title'], 'Attleboro Youth Baseball')
        listings = list(response.context['listings'])
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].pk, attleboro_baseball.pk)

    def test_sports_slug_route_filters_by_subtype(self):
        baseball = Listing.objects.create(
            title='Attleboro Baseball League',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Attleboro Youth Baseball',
            city_town='Attleboro',
            location_name='Town Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/attleboro-baseball',
            description='Town baseball program',
            status=Listing.Status.PUBLISHED,
        )

        response = self.client.get(reverse('core:sports_subtype', kwargs={'subtype_slug': 'baseball'}))
        self.assertEqual(response.status_code, 200)
        listings = list(response.context['listings'])
        self.assertIn(baseball, listings)
        self.assertNotIn(self.sports_future, listings)

    def test_sports_slug_route_filters_by_subtype_and_city(self):
        baseball_attleboro = Listing.objects.create(
            title='Attleboro Baseball League',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Attleboro Youth Baseball',
            city_town='Attleboro',
            location_name='Town Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/attleboro-baseball',
            description='Town baseball program',
            status=Listing.Status.PUBLISHED,
        )
        Listing.objects.create(
            title='Mansfield Baseball League',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Mansfield Youth Baseball',
            city_town='Mansfield',
            location_name='Baseball Complex',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/mansfield-baseball',
            description='Town baseball program',
            status=Listing.Status.PUBLISHED,
        )

        response = self.client.get(
            reverse(
                'core:sports_subtype_city',
                kwargs={'subtype_slug': 'baseball', 'city_slug': 'attleboro'},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_title'], 'Attleboro Youth Baseball')
        listings = list(response.context['listings'])
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].pk, baseball_attleboro.pk)

    def test_sports_search_matches_common_typo(self):
        baseball = Listing.objects.create(
            title='Attleboro Baseball League',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Attleboro Youth Baseball',
            city_town='Attleboro',
            location_name='Town Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/attleboro-baseball',
            description='Town baseball program',
            status=Listing.Status.PUBLISHED,
        )
        response = self.client.get(reverse('core:sports'), {'q': 'basball'})
        self.assertEqual(response.status_code, 200)
        listings = list(response.context['listings'])
        self.assertIn(baseball, listings)
        self.assertTrue(
            ListingAnalyticsEvent.objects.filter(
                event_type=ListingAnalyticsEvent.EventType.SEARCH,
                query='basball',
                section=Listing.Category.SPORT,
            ).exists()
        )

    def test_search_with_no_results_logs_empty_search_event(self):
        response = self.client.get(reverse('core:sports'), {'q': 'zzzz-unlikely-query'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            ListingAnalyticsEvent.objects.filter(
                event_type=ListingAnalyticsEvent.EventType.EMPTY_SEARCH,
                query='zzzz-unlikely-query',
                section=Listing.Category.SPORT,
            ).exists()
        )

    def test_sports_sort_recent_orders_by_created_at_desc(self):
        older = Listing.objects.create(
            title='Older Listing',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Org A',
            city_town='Attleboro',
            location_name='Field A',
            age_min=7,
            age_max=10,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/older',
            description='Older',
            status=Listing.Status.PUBLISHED,
        )
        newer = Listing.objects.create(
            title='Newer Listing',
            category=Listing.Category.SPORT,
            subtype='Soccer',
            organization_name='Org B',
            city_town='Attleboro',
            location_name='Field B',
            age_min=7,
            age_max=10,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/newer',
            description='Newer',
            status=Listing.Status.PUBLISHED,
        )
        response = self.client.get(reverse('core:sports'), {'sort': 'recent'})
        self.assertEqual(response.status_code, 200)
        listings = list(response.context['listings'])
        self.assertLess(listings.index(newer), listings.index(older))

    def test_listing_detail_is_available_for_active_and_404_for_inactive(self):
        active_response = self.client.get(
            reverse('core:listing_detail', kwargs={'pk': self.sports_future.pk})
        )
        self.assertEqual(active_response.status_code, 200)

        inactive_response = self.client.get(
            reverse('core:listing_detail', kwargs={'pk': self.inactive_listing.pk})
        )
        self.assertEqual(inactive_response.status_code, 404)

    def test_listing_detail_accepts_outdated_report_submission(self):
        response = self.client.post(
            reverse('core:listing_detail', kwargs={'pk': self.sports_future.pk}),
            data={
                'reporter_email': 'parent@example.com',
                'notes': 'Registration dates appear to be old.',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ListingOutdatedReport.objects.count(), 1)
        report = ListingOutdatedReport.objects.get()
        self.assertEqual(report.listing_id, self.sports_future.id)
        self.assertEqual(report.reporter_email, 'parent@example.com')

    def test_listing_detail_rejects_empty_outdated_report_notes(self):
        response = self.client.post(
            reverse('core:listing_detail', kwargs={'pk': self.sports_future.pk}),
            data={
                'reporter_email': 'parent@example.com',
                'notes': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertEqual(ListingOutdatedReport.objects.count(), 0)

    def test_robots_txt_exposes_sitemap_location(self):
        response = self.client.get(reverse('core:robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User-agent: *')
        self.assertContains(response, '/sitemap.xml')

    def test_sitemap_includes_core_routes_and_published_listing(self):
        response = self.client.get(reverse('core:sitemap_xml'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<urlset')
        self.assertContains(response, reverse('core:home'))
        self.assertContains(response, reverse('core:sports'))
        self.assertContains(response, reverse('core:listing_detail', kwargs={'pk': self.sports_future.pk}))

    def test_outbound_redirect_logs_click_event(self):
        response = self.client.get(reverse('core:listing_outbound', kwargs={'pk': self.sports_future.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], self.sports_future.registration_url)
        self.assertTrue(
            ListingAnalyticsEvent.objects.filter(
                event_type=ListingAnalyticsEvent.EventType.OUTBOUND_CLICK,
                listing=self.sports_future,
                target_url=self.sports_future.registration_url,
            ).exists()
        )
