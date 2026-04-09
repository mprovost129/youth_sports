from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class State(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=2, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


class County(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='counties')
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['state', 'name'], name='unique_county_per_state'),
        ]

    def __str__(self):
        return f'{self.name}, {self.state.code}'


class CityTown(models.Model):
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='cities_towns')
    name = models.CharField(max_length=120)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['county', 'name'], name='unique_city_town_per_county'),
        ]

    def __str__(self):
        return f'{self.name}, {self.county.name}'


class SportType(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ActivityType(models.Model):
    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Listing(models.Model):
    class Category(models.TextChoices):
        SPORT = 'sport', 'Sport'
        ACTIVITY = 'activity', 'Activity'

    class Gender(models.TextChoices):
        BOYS = 'boys', 'Boys'
        GIRLS = 'girls', 'Girls'
        COED = 'coed', 'Co-ed'
        NOT_SPECIFIED = 'not_specified', 'Not specified'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices)
    subtype = models.CharField(max_length=100)
    sport_type = models.ForeignKey(
        SportType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listings',
    )
    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listings',
    )
    organization_name = models.CharField(max_length=255)
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listings',
    )
    county = models.ForeignKey(
        County,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listings',
    )
    city_town_ref = models.ForeignKey(
        CityTown,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listings',
    )
    city_town = models.CharField(max_length=120)
    location_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    age_min = models.PositiveSmallIntegerField()
    age_max = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.NOT_SPECIFIED)
    season_or_dates = models.CharField(max_length=255)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    registration_url = models.URLField()
    image = models.FileField(
        upload_to='listing_images/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'])],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_listings',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_listings',
    )
    cost = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    last_verified_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['city_town']),
            models.Index(fields=['gender']),
            models.Index(fields=['status']),
            models.Index(fields=['subtype']),
            models.Index(fields=['last_verified_at']),
            models.Index(fields=['start_date']),
            models.Index(fields=['status', 'last_verified_at']),
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['status', 'category', 'subtype', 'city_town_ref']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age_max__gte=models.F('age_min')),
                name='listing_age_max_gte_age_min',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(start_date__isnull=True)
                    | models.Q(end_date__isnull=True)
                    | models.Q(end_date__gte=models.F('start_date'))
                ),
                name='listing_end_date_gte_start_date',
            ),
        ]

    def __str__(self):
        return f'{self.title} ({self.city_town})'

    @property
    def is_stale(self):
        stale_threshold = timezone.now() - timezone.timedelta(days=90)
        return self.last_verified_at < stale_threshold

    @property
    def verification_label(self):
        return 'Needs review' if self.is_stale else 'Verified recently'


class ListingOutdatedReport(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='outdated_reports')
    reporter_email = models.EmailField(blank=True)
    notes = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['resolved']),
        ]

    def __str__(self):
        return f'Report for {self.listing.title} ({self.created_at:%Y-%m-%d})'


class ListingChangeLog(models.Model):
    class Action(models.TextChoices):
        CREATED = 'created', 'Created'
        EDITED = 'edited', 'Edited'
        PUBLISHED = 'published', 'Published'

    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='change_logs')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='listing_change_logs',
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    changed_fields = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['action']),
        ]

    def __str__(self):
        return f'{self.get_action_display()} - {self.listing.title}'


class ListingSuggestion(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Listing.Category.choices)
    subtype = models.CharField(max_length=100)
    sport_type = models.ForeignKey(
        SportType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions',
    )
    activity_type = models.ForeignKey(
        ActivityType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions',
    )
    organization_name = models.CharField(max_length=255)
    state = models.ForeignKey(
        State,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions',
    )
    county = models.ForeignKey(
        County,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions',
    )
    city_town_ref = models.ForeignKey(
        CityTown,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='suggestions',
    )
    city_town = models.CharField(max_length=120)
    location_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True)
    age_min = models.PositiveSmallIntegerField()
    age_max = models.PositiveSmallIntegerField()
    gender = models.CharField(max_length=20, choices=Listing.Gender.choices, default=Listing.Gender.NOT_SPECIFIED)
    season_or_dates = models.CharField(max_length=255)
    registration_url = models.URLField()
    image = models.FileField(
        upload_to='listing_suggestions/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'])],
    )
    description = models.TextField()
    submitter_name = models.CharField(max_length=150, blank=True)
    submitter_email = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_suggestions',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_suggestions',
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age_max__gte=models.F('age_min')),
                name='suggestion_age_max_gte_age_min',
            ),
        ]

    def __str__(self):
        return f'Suggestion: {self.title} ({self.status})'


class ListingAnalyticsEvent(models.Model):
    class EventType(models.TextChoices):
        SEARCH = 'search', 'Search'
        EMPTY_SEARCH = 'empty_search', 'Empty search'
        OUTBOUND_CLICK = 'outbound_click', 'Outbound click'

    event_type = models.CharField(max_length=30, choices=EventType.choices)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events',
    )
    section = models.CharField(max_length=30, blank=True)
    query = models.CharField(max_length=255, blank=True)
    subtype = models.CharField(max_length=120, blank=True)
    city_town = models.CharField(max_length=120, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    target_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['query']),
            models.Index(fields=['section']),
        ]

    def __str__(self):
        return f'{self.event_type} ({self.created_at:%Y-%m-%d %H:%M})'
