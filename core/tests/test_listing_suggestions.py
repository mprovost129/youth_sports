from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import CityTown, County, Listing, ListingSuggestion, SportType, State


class ListingSuggestionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            email='suggest-staff@example.com',
            password='password123',
            is_staff=True,
        )
        self.state, _ = State.objects.get_or_create(code='MA', defaults={'name': 'Massachusetts'})
        self.county, _ = County.objects.get_or_create(state=self.state, name='Bristol')
        self.city, _ = CityTown.objects.get_or_create(county=self.county, name='Attleboro')
        self.sport, _ = SportType.objects.get_or_create(name='Baseball')

    def test_public_can_access_suggest_form(self):
        response = self.client.get(reverse('core:suggest_listing'))
        self.assertEqual(response.status_code, 200)

    def test_public_can_submit_suggestion(self):
        response = self.client.post(
            reverse('core:suggest_listing'),
            data={
                'listing_type': Listing.Category.SPORT,
                'state': self.state.pk,
                'county': self.county.pk,
                'city_town_ref': self.city.pk,
                'city_town_manual': '',
                'sport_type': self.sport.pk,
                'custom_sport': '',
                'activity_type': '',
                'custom_activity': '',
                'title': 'Community Baseball Suggestion',
                'organization_name': 'Community Sports',
                'location_name': 'Town Field',
                'address': '',
                'age_min': 7,
                'age_max': 12,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring',
                'description': 'Public suggestion',
                'registration_url': 'https://example.com/suggest',
                'submitter_name': 'Parent User',
                'submitter_email': 'parent@example.com',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        suggestion = ListingSuggestion.objects.get(title='Community Baseball Suggestion')
        self.assertEqual(suggestion.status, ListingSuggestion.Status.PENDING)

    def test_staff_can_approve_suggestion_and_publish_listing(self):
        suggestion = ListingSuggestion.objects.create(
            title='Approve Me',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            sport_type=self.sport,
            organization_name='Community Sports',
            state=self.state,
            county=self.county,
            city_town_ref=self.city,
            city_town='Attleboro',
            location_name='Town Field',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/approve',
            description='Pending suggestion',
            status=ListingSuggestion.Status.PENDING,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:verification_queue'),
            data={'action': 'approve_suggestion', 'suggestion_id': suggestion.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, ListingSuggestion.Status.APPROVED)
        self.assertIsNotNone(suggestion.approved_listing_id)
        self.assertEqual(suggestion.approved_listing.status, Listing.Status.PUBLISHED)

    def test_staff_can_reject_suggestion(self):
        suggestion = ListingSuggestion.objects.create(
            title='Reject Me',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            sport_type=self.sport,
            organization_name='Community Sports',
            state=self.state,
            county=self.county,
            city_town_ref=self.city,
            city_town='Attleboro',
            location_name='Town Field',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/reject',
            description='Pending suggestion',
            status=ListingSuggestion.Status.PENDING,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:verification_queue'),
            data={'action': 'reject_suggestion', 'suggestion_id': suggestion.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, ListingSuggestion.Status.REJECTED)

    def test_public_location_endpoints_for_suggest_form(self):
        county_response = self.client.get(
            reverse('core:public_counties_by_state'),
            {'state_id': self.state.pk},
        )
        self.assertEqual(county_response.status_code, 200)
        county_names = [item['name'] for item in county_response.json()['results']]
        self.assertIn('Bristol', county_names)

        city_response = self.client.get(
            reverse('core:public_cities_by_county'),
            {'county_id': self.county.pk},
        )
        self.assertEqual(city_response.status_code, 200)
        city_names = [item['name'] for item in city_response.json()['results']]
        self.assertIn('Attleboro', city_names)

    def test_public_suggest_blocks_likely_duplicate_without_override(self):
        Listing.objects.create(
            title='Community Baseball Suggestion',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Community Sports',
            state=self.state,
            county=self.county,
            city_town_ref=self.city,
            city_town='Attleboro',
            location_name='Town Field',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/suggest',
            description='Existing listing',
            status=Listing.Status.PUBLISHED,
        )
        response = self.client.post(
            reverse('core:suggest_listing'),
            data={
                'listing_type': Listing.Category.SPORT,
                'state': self.state.pk,
                'county': self.county.pk,
                'city_town_ref': self.city.pk,
                'city_town_manual': '',
                'sport_type': self.sport.pk,
                'custom_sport': '',
                'activity_type': '',
                'custom_activity': '',
                'title': 'Community Baseball Suggestion',
                'organization_name': 'Community Sports',
                'location_name': 'Town Field',
                'address': '',
                'age_min': 7,
                'age_max': 12,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring',
                'description': 'Public suggestion',
                'registration_url': 'https://example.com/suggest',
                'submitter_name': 'Parent User',
                'submitter_email': 'parent@example.com',
                'confirm_possible_duplicate': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Possible duplicate listing found')
        self.assertEqual(ListingSuggestion.objects.count(), 0)
