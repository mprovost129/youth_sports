from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import (
    CityTown,
    County,
    Listing,
    ListingChangeLog,
    SportType,
    State,
)


class ListingAuditTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff_user = User.objects.create_user(
            email='audit-staff@example.com',
            password='password123',
            is_staff=True,
        )

        self.state, _ = State.objects.get_or_create(code='MA', defaults={'name': 'Massachusetts'})
        self.county, _ = County.objects.get_or_create(state=self.state, name='Bristol')
        self.city, _ = CityTown.objects.get_or_create(county=self.county, name='Attleboro')
        self.sport, _ = SportType.objects.get_or_create(name='Baseball')

    def test_create_listing_sets_creator_and_writes_change_log(self):
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
                'organization_name': 'Audit Baseball',
                'location_name': 'Field A',
                'address': '',
                'age_min': 8,
                'age_max': 12,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring',
                'description': 'Audit create',
                'registration_url': 'https://example.com/audit-create',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        listing = Listing.objects.get(organization_name='Audit Baseball')
        self.assertEqual(listing.created_by_id, self.staff_user.id)
        self.assertEqual(listing.updated_by_id, self.staff_user.id)
        log = ListingChangeLog.objects.get(listing=listing)
        self.assertEqual(log.action, ListingChangeLog.Action.CREATED)
        self.assertEqual(log.actor_id, self.staff_user.id)

    def test_edit_listing_writes_edited_change_log(self):
        listing = Listing.objects.create(
            title='Audit Listing',
            category=Listing.Category.SPORT,
            subtype='Baseball',
            sport_type=self.sport,
            organization_name='Audit Org',
            state=self.state,
            county=self.county,
            city_town_ref=self.city,
            city_town='Attleboro',
            location_name='Field B',
            age_min=8,
            age_max=12,
            gender=Listing.Gender.COED,
            season_or_dates='Spring',
            registration_url='https://example.com/original',
            description='Before edit',
            status=Listing.Status.PUBLISHED,
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
                'organization_name': 'Audit Org Updated',
                'location_name': listing.location_name,
                'address': '',
                'age_min': 8,
                'age_max': 13,
                'gender': Listing.Gender.COED,
                'season_or_dates': 'Spring',
                'description': 'After edit',
                'registration_url': 'https://example.com/updated',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        listing.refresh_from_db()
        self.assertEqual(listing.updated_by_id, self.staff_user.id)
        edit_log = ListingChangeLog.objects.filter(
            listing=listing, action=ListingChangeLog.Action.EDITED
        ).first()
        self.assertIsNotNone(edit_log)
        self.assertIn('organization_name', edit_log.changed_fields)
        self.assertIn('status', edit_log.changed_fields)
