from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('sitemap.xml', views.SitemapXmlView.as_view(), name='sitemap_xml'),
    path('robots.txt', views.RobotsTxtView.as_view(), name='robots_txt'),
    path('sports/', views.SportsListView.as_view(), name='sports'),
    path(
        'sports/<slug:subtype_slug>/',
        views.SportsSubtypeListView.as_view(),
        name='sports_subtype',
    ),
    path(
        'sports/<slug:subtype_slug>/<slug:city_slug>/',
        views.SportsSubtypeCityListView.as_view(),
        name='sports_subtype_city',
    ),
    path('activities/', views.ActivitiesListView.as_view(), name='activities'),
    path(
        'activities/<slug:subtype_slug>/',
        views.ActivitiesSubtypeListView.as_view(),
        name='activities_subtype',
    ),
    path(
        'activities/<slug:subtype_slug>/<slug:city_slug>/',
        views.ActivitiesSubtypeCityListView.as_view(),
        name='activities_subtype_city',
    ),
    path('suggest-listing/', views.SuggestListingView.as_view(), name='suggest_listing'),
    path('listings/<int:pk>/', views.ListingDetailView.as_view(), name='listing_detail'),
    path('listings/<int:pk>/visit/', views.OutboundListingRedirectView.as_view(), name='listing_outbound'),
    path('admin-tools/add-new/', views.AddNewListingView.as_view(), name='add_new_listing'),
    path('admin-tools/listings/<int:pk>/edit/', views.EditListingView.as_view(), name='edit_listing'),
    path('admin-tools/verification-queue/', views.VerificationQueueView.as_view(), name='verification_queue'),
    path('admin-tools/counties/', views.CountiesByStateView.as_view(), name='counties_by_state'),
    path('admin-tools/cities/', views.CitiesByCountyView.as_view(), name='cities_by_county'),
    path('suggest/counties/', views.PublicCountiesByStateView.as_view(), name='public_counties_by_state'),
    path('suggest/cities/', views.PublicCitiesByCountyView.as_view(), name='public_cities_by_county'),
    path('resources/', views.ResourcesView.as_view(), name='resources'),
    path('contact/', views.ContactView.as_view(), name='contact'),
]
