from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from .image_utils import process_listing_image
from .models import (
    ActivityType,
    CityTown,
    County,
    Listing,
    ListingOutdatedReport,
    ListingSuggestion,
    SportType,
    State,
)


class AddNewListingForm(forms.Form):
    listing_type_choices = [
        (Listing.Category.SPORT, 'Organized Sport'),
        (Listing.Category.ACTIVITY, 'Activity'),
    ]

    listing_type = forms.ChoiceField(
        choices=listing_type_choices,
        label='Type',
        help_text='Choose Organized Sport or Activity.',
    )
    state = forms.ModelChoiceField(queryset=State.objects.all(), empty_label='Select state')
    county = forms.ModelChoiceField(queryset=County.objects.none(), empty_label='Select county')
    city_town_ref = forms.ModelChoiceField(
        queryset=CityTown.objects.none(),
        required=False,
        label='City/Town',
        empty_label='Select city/town',
    )
    city_town_manual = forms.CharField(required=False, label='City/Town (manual)')

    sport_type = forms.ModelChoiceField(
        queryset=SportType.objects.all(),
        required=False,
        empty_label='Select sport',
    )
    custom_sport = forms.CharField(required=False, label='Sport (manual)')

    activity_type = forms.ModelChoiceField(
        queryset=ActivityType.objects.all(),
        required=False,
        empty_label='Select activity',
    )
    custom_activity = forms.CharField(required=False, label='Activity (manual)')

    title = forms.CharField(required=False, max_length=255)
    organization_name = forms.CharField(max_length=255)
    location_name = forms.CharField(max_length=255)
    address = forms.CharField(required=False, max_length=255)
    age_min = forms.IntegerField(min_value=1, max_value=18)
    age_max = forms.IntegerField(min_value=1, max_value=18)
    gender = forms.ChoiceField(choices=Listing.Gender.choices, initial=Listing.Gender.NOT_SPECIFIED)
    season_or_dates = forms.CharField(max_length=255)
    description = forms.CharField(widget=forms.Textarea)
    registration_url = forms.URLField(max_length=500)
    image = forms.FileField(
        required=False,
        help_text='Optional. Max 5MB. Recommended at least 120x120px.',
    )
    confirm_possible_duplicate = forms.BooleanField(
        required=False,
        label='I reviewed possible duplicates and want to continue.',
    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)

        self.fields['sport_type'].queryset = SportType.objects.all().order_by('name')
        self.fields['activity_type'].queryset = ActivityType.objects.all().order_by('name')

        state_id = self._state_id_from_data()
        county_id = self._county_id_from_data()

        if state_id:
            self.fields['county'].queryset = County.objects.filter(state_id=state_id).order_by('name')
        if county_id:
            self.fields['city_town_ref'].queryset = CityTown.objects.filter(county_id=county_id).order_by('name')

        for name, field in self.fields.items():
            css_class = 'form-select' if isinstance(field, forms.ModelChoiceField | forms.ChoiceField) else 'form-control'
            if isinstance(field, forms.BooleanField):
                css_class = 'form-check-input'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (f'{existing} {css_class}').strip()

    def _state_id_from_data(self):
        value = self.data.get('state') or self.initial.get('state')
        return int(value) if str(value).isdigit() else None

    def _county_id_from_data(self):
        value = self.data.get('county') or self.initial.get('county')
        return int(value) if str(value).isdigit() else None

    def clean(self):
        cleaned = super().clean()

        age_min = cleaned.get('age_min')
        age_max = cleaned.get('age_max')
        if age_min is not None and age_max is not None and age_max < age_min:
            raise ValidationError('Age max must be greater than or equal to age min.')

        state = cleaned.get('state')
        county = cleaned.get('county')
        city_ref = cleaned.get('city_town_ref')
        city_manual = (cleaned.get('city_town_manual') or '').strip()

        if county and state and county.state_id != state.id:
            raise ValidationError('Selected county does not belong to the selected state.')
        if city_ref and county and city_ref.county_id != county.id:
            raise ValidationError('Selected city/town does not belong to the selected county.')
        if not city_ref and not city_manual:
            raise ValidationError('Select a city/town or enter one manually.')

        listing_type = cleaned.get('listing_type')
        sport_type = cleaned.get('sport_type')
        custom_sport = (cleaned.get('custom_sport') or '').strip()
        activity_type = cleaned.get('activity_type')
        custom_activity = (cleaned.get('custom_activity') or '').strip()

        if listing_type == Listing.Category.SPORT:
            if not sport_type and not custom_sport:
                raise ValidationError('Choose a sport or enter one manually.')
        elif listing_type == Listing.Category.ACTIVITY:
            if not activity_type and not custom_activity:
                raise ValidationError('Choose an activity or enter one manually.')

        if all(
            cleaned.get(key)
            for key in ['listing_type', 'organization_name', 'location_name', 'registration_url']
        ):
            values = self._build_listing_values(cleaned)
            duplicate_matches = self._find_possible_duplicates(values)
            if duplicate_matches and not cleaned.get('confirm_possible_duplicate'):
                preview = ', '.join(match.title for match in duplicate_matches[:3])
                raise ValidationError(
                    'Possible duplicate listing found. Matching listing(s): '
                    f'{preview}. Check the duplicate override box if you still want to continue.'
                )

        return cleaned

    def _find_possible_duplicates(self, values):
        queryset = Listing.objects.filter(
            category=values['category'],
            subtype__iexact=values['subtype'],
            city_town__iexact=values['city_town'],
        ).filter(
            Q(title__iexact=values['title'])
            | Q(organization_name__iexact=values['organization_name'])
            | Q(location_name__iexact=values['location_name'])
            | Q(registration_url__iexact=values['registration_url'])
        )

        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        return list(queryset.order_by('-updated_at')[:5])

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if not image:
            return image
        return process_listing_image(image)

    def _build_listing_values(self, cleaned):
        listing_type = cleaned['listing_type']
        city_ref = cleaned.get('city_town_ref')
        city_town = city_ref.name if city_ref else cleaned['city_town_manual'].strip()

        subtype = ''
        sport_type = None
        activity_type = None
        if listing_type == Listing.Category.SPORT:
            sport_type = cleaned.get('sport_type')
            subtype = sport_type.name if sport_type else cleaned.get('custom_sport', '').strip()
        else:
            activity_type = cleaned.get('activity_type')
            subtype = (
                activity_type.name if activity_type else cleaned.get('custom_activity', '').strip()
            )

        title = (cleaned.get('title') or '').strip()
        if not title:
            title = f'{city_town} Youth {subtype}'

        return {
            'title': title,
            'category': listing_type,
            'subtype': subtype,
            'sport_type': sport_type,
            'activity_type': activity_type,
            'organization_name': cleaned['organization_name'],
            'state': cleaned['state'],
            'county': cleaned['county'],
            'city_town_ref': city_ref,
            'city_town': city_town,
            'location_name': cleaned['location_name'],
            'address': cleaned.get('address', '').strip(),
            'age_min': cleaned['age_min'],
            'age_max': cleaned['age_max'],
            'gender': cleaned['gender'],
            'season_or_dates': cleaned['season_or_dates'],
            'registration_url': cleaned['registration_url'],
            'description': cleaned['description'],
            'image': cleaned.get('image'),
        }

    def save(self, instance=None, user=None):
        cleaned = self.cleaned_data
        values = self._build_listing_values(cleaned)

        target = instance or Listing()
        target.title = values['title']
        target.category = values['category']
        target.subtype = values['subtype']
        target.sport_type = values['sport_type']
        target.activity_type = values['activity_type']
        target.organization_name = values['organization_name']
        target.state = values['state']
        target.county = values['county']
        target.city_town_ref = values['city_town_ref']
        target.city_town = values['city_town']
        target.location_name = values['location_name']
        target.address = values['address']
        target.age_min = values['age_min']
        target.age_max = values['age_max']
        target.gender = values['gender']
        target.season_or_dates = values['season_or_dates']
        target.registration_url = values['registration_url']
        target.description = values['description']
        target.status = Listing.Status.DRAFT
        if user and getattr(user, 'is_authenticated', False):
            if not target.pk and target.created_by_id is None:
                target.created_by = user
            target.updated_by = user

        new_image = values.get('image')
        if new_image:
            target.image = new_image

        target.save()
        return target


class SuggestListingForm(AddNewListingForm):
    submitter_name = forms.CharField(required=False, max_length=150)
    submitter_email = forms.EmailField(required=False)

    def save_suggestion(self):
        values = self._build_listing_values(self.cleaned_data)
        suggestion = ListingSuggestion.objects.create(
            title=values['title'],
            category=values['category'],
            subtype=values['subtype'],
            sport_type=values['sport_type'],
            activity_type=values['activity_type'],
            organization_name=values['organization_name'],
            state=values['state'],
            county=values['county'],
            city_town_ref=values['city_town_ref'],
            city_town=values['city_town'],
            location_name=values['location_name'],
            address=values['address'],
            age_min=values['age_min'],
            age_max=values['age_max'],
            gender=values['gender'],
            season_or_dates=values['season_or_dates'],
            registration_url=values['registration_url'],
            image=values['image'],
            description=values['description'],
            submitter_name=(self.cleaned_data.get('submitter_name') or '').strip(),
            submitter_email=(self.cleaned_data.get('submitter_email') or '').strip(),
            status=ListingSuggestion.Status.PENDING,
        )
        return suggestion


class OutdatedListingReportForm(forms.ModelForm):
    class Meta:
        model = ListingOutdatedReport
        fields = ['reporter_email', 'notes']
        labels = {
            'reporter_email': 'Email (optional)',
            'notes': 'What looks outdated?',
        }
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['reporter_email'].required = False
        self.fields['reporter_email'].widget.attrs['class'] = 'form-control'
        self.fields['notes'].widget.attrs['class'] = 'form-control'
