from django.contrib import admin

from .models import (
    ActivityType,
    CityTown,
    County,
    Listing,
    ListingChangeLog,
    ListingAnalyticsEvent,
    ListingOutdatedReport,
    ListingSuggestion,
    SportType,
    State,
)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'category',
        'subtype',
        'city_town',
        'gender',
        'start_date',
        'end_date',
        'status',
        'created_by',
        'updated_by',
        'last_verified_at',
    )
    list_filter = ('category', 'city_town', 'gender', 'status')
    search_fields = ('title', 'subtype', 'organization_name', 'city_town')
    ordering = ('title',)


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(County)
class CountyAdmin(admin.ModelAdmin):
    list_display = ('name', 'state')
    list_filter = ('state',)
    search_fields = ('name', 'state__name', 'state__code')
    ordering = ('state__name', 'name')


@admin.register(CityTown)
class CityTownAdmin(admin.ModelAdmin):
    list_display = ('name', 'county')
    list_filter = ('county__state', 'county')
    search_fields = ('name', 'county__name', 'county__state__name')
    ordering = ('county__state__name', 'county__name', 'name')


@admin.register(SportType)
class SportTypeAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(ListingOutdatedReport)
class ListingOutdatedReportAdmin(admin.ModelAdmin):
    list_display = ('listing', 'reporter_email', 'created_at', 'resolved')
    list_filter = ('resolved', 'created_at')
    search_fields = ('listing__title', 'listing__organization_name', 'reporter_email', 'notes')
    ordering = ('-created_at',)


@admin.register(ListingChangeLog)
class ListingChangeLogAdmin(admin.ModelAdmin):
    list_display = ('listing', 'action', 'actor', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('listing__title', 'actor__email', 'notes')
    ordering = ('-created_at',)


@admin.register(ListingSuggestion)
class ListingSuggestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'city_town', 'status', 'submitter_email', 'created_at')
    list_filter = ('status', 'category', 'city_town')
    search_fields = ('title', 'organization_name', 'subtype', 'city_town', 'submitter_email')
    ordering = ('-created_at',)


@admin.register(ListingAnalyticsEvent)
class ListingAnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'section', 'query', 'subtype', 'city_town', 'result_count', 'created_at')
    list_filter = ('event_type', 'section', 'created_at')
    search_fields = ('query', 'subtype', 'city_town', 'target_url', 'listing__title')
    ordering = ('-created_at',)
