from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import CityTown, County, Listing, SportType, State


class AddNewListingFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='password123',
            is_staff=True,
        )
        self.normal_user = User.objects.create_user(
            email='user@example.com',
            password='password123',
            is_staff=False,
        )

        self.state, _ = State.objects.get_or_create(code='MA', defaults={'name': 'Massachusetts'})
        self.county, _ = County.objects.get_or_create(state=self.state, name='Bristol')
        self.city, _ = CityTown.objects.get_or_create(county=self.county, name='Attleboro')
        self.sport, _ = SportType.objects.get_or_create(name='Baseball')

    def test_add_new_requires_staff(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('core:add_new_listing'))
        self.assertEqual(response.status_code, 403)

    def test_add_new_creates_listing_for_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:add_new_listing'),
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
                'title': '',
                'organization_name': 'Attleboro Youth Baseball',
                'location_name': 'Town Diamond',
                'address': '123 Main St',
                'age_min': 7,
                'age_max': 12,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring',
                'description': 'Town baseball program',
                'registration_url': 'https://example.com/attleboro-baseball',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        listing = Listing.objects.get()
        self.assertEqual(listing.category, Listing.Category.SPORT)
        self.assertEqual(listing.subtype, 'Baseball')
        self.assertEqual(listing.city_town, 'Attleboro')
        self.assertEqual(listing.state_id, self.state.pk)
        self.assertEqual(listing.county_id, self.county.pk)
        self.assertEqual(listing.city_town_ref_id, self.city.pk)
        self.assertEqual(listing.title, 'Attleboro Youth Baseball')
        self.assertEqual(listing.status, Listing.Status.DRAFT)

    def test_county_and_city_endpoints_return_db_driven_options(self):
        self.client.force_login(self.staff_user)

        county_response = self.client.get(
            reverse('core:counties_by_state'),
            {'state_id': self.state.pk},
        )
        self.assertEqual(county_response.status_code, 200)
        county_names = [item['name'] for item in county_response.json()['results']]
        self.assertIn('Bristol', county_names)

        city_response = self.client.get(
            reverse('core:cities_by_county'),
            {'county_id': self.county.pk},
        )
        self.assertEqual(city_response.status_code, 200)
        city_names = [item['name'] for item in city_response.json()['results']]
        self.assertIn('Attleboro', city_names)

    def test_add_new_allows_manual_sport_entry(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:add_new_listing'),
            data={
                'listing_type': Listing.Category.SPORT,
                'state': self.state.pk,
                'county': self.county.pk,
                'city_town_ref': '',
                'city_town_manual': 'Attleboro',
                'sport_type': '',
                'custom_sport': 'Cricket',
                'activity_type': '',
                'custom_activity': '',
                'title': '',
                'organization_name': 'Attleboro Community Sports',
                'location_name': 'Community Field',
                'address': '',
                'age_min': 9,
                'age_max': 13,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Summer',
                'description': 'Manual sport entry flow',
                'registration_url': 'https://example.com/cricket',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        listing = Listing.objects.get(organization_name='Attleboro Community Sports')
        self.assertEqual(listing.subtype, 'Cricket')
        self.assertIsNone(listing.sport_type)

    def test_edit_listing_requires_staff(self):
        listing = Listing.objects.create(
            title='Editable Listing',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='League',
            city_town='Attleboro',
            location_name='Field',
            age_min=8,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/editable',
            description='Original',
        )
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('core:edit_listing', kwargs={'pk': listing.pk}))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_edit_existing_listing(self):
        listing = Listing.objects.create(
            title='Attleboro Youth Baseball',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            sport_type=self.sport,
            organization_name='Attleboro Youth Baseball',
            state=self.state,
            county=self.county,
            city_town_ref=self.city,
            city_town='Attleboro',
            location_name='Town Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/old',
            description='Before edit',
        )

        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:edit_listing', kwargs={'pk': listing.pk}),
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
                'title': listing.title,
                'organization_name': 'Attleboro Baseball Association',
                'location_name': listing.location_name,
                'address': '',
                'age_min': 7,
                'age_max': 13,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring / Summer',
                'description': 'After edit',
                'registration_url': 'https://example.com/new',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        listing.refresh_from_db()
        self.assertEqual(listing.organization_name, 'Attleboro Baseball Association')
        self.assertEqual(listing.age_max, 13)
        self.assertEqual(listing.season_or_dates, 'Spring / Summer')
        self.assertEqual(listing.registration_url, 'https://example.com/new')
        self.assertEqual(listing.status, Listing.Status.DRAFT)

    def test_add_new_blocks_likely_duplicate_without_override(self):
        Listing.objects.create(
            title='Attleboro Youth Baseball',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Attleboro Youth Baseball',
            state=self.state,
            county=self.county,
            city_town_ref=self.city,
            city_town='Attleboro',
            location_name='Town Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/attleboro-baseball',
            description='Existing listing',
            status=Listing.Status.PUBLISHED,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:add_new_listing'),
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
                'title': 'Attleboro Youth Baseball',
                'organization_name': 'Attleboro Youth Baseball',
                'location_name': 'Town Diamond',
                'address': '123 Main St',
                'age_min': 7,
                'age_max': 12,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring',
                'description': 'Town baseball program',
                'registration_url': 'https://example.com/attleboro-baseball',
                'confirm_possible_duplicate': '',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Possible duplicate listing found')
        self.assertEqual(Listing.objects.count(), 1)

    def test_add_new_allows_likely_duplicate_with_override_checked(self):
        Listing.objects.create(
            title='Attleboro Youth Baseball',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            organization_name='Attleboro Youth Baseball',
            state=self.state,
            county=self.county,
            city_town_ref=self.city,
            city_town='Attleboro',
            location_name='Town Diamond',
            age_min=7,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/attleboro-baseball',
            description='Existing listing',
            status=Listing.Status.PUBLISHED,
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            reverse('core:add_new_listing'),
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
                'title': 'Attleboro Youth Baseball',
                'organization_name': 'Attleboro Youth Baseball',
                'location_name': 'Town Diamond',
                'address': '123 Main St',
                'age_min': 7,
                'age_max': 12,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring',
                'description': 'Town baseball program',
                'registration_url': 'https://example.com/attleboro-baseball',
                'confirm_possible_duplicate': 'on',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Listing.objects.count(), 2)
