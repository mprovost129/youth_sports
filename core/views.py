import json
from difflib import SequenceMatcher
from xml.sax.saxutils import escape

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Case, F, IntegerField, Max, Q, When
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from .forms import AddNewListingForm, OutdatedListingReportForm, SuggestListingForm
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
)


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class HomeView(TemplateView):
    template_name = 'core/home.html'
    cache_ttl_seconds = 300

    def _ordered_listings_from_ids(self, ids):
        if not ids:
            return Listing.objects.none()
        ordering = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(ids)],
            output_field=IntegerField(),
        )
        return Listing.objects.filter(pk__in=ids).order_by(ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cache_key = f'home:v1:cards:{self._cache_version()}'
        cached_payload = cache.get(cache_key)

        if cached_payload is None:
            active_listings = Listing.objects.filter(status=Listing.Status.PUBLISHED)
            today = timezone.localdate()
            cached_payload = {
                'upcoming_ids': list(
                    active_listings.filter(Q(start_date__gte=today) | Q(start_date__isnull=True))
                    .order_by(F('start_date').asc(nulls_last=True), 'title')
                    .values_list('id', flat=True)[:6]
                ),
                'recent_ids': list(
                    active_listings.order_by('-created_at').values_list('id', flat=True)[:6]
                ),
                'popular_sports': list(
                    active_listings.filter(category=Listing.Category.SPORT)
                    .exclude(subtype='')
                    .values_list('subtype', flat=True)
                    .distinct()[:8]
                ),
                'popular_towns': list(
                    active_listings.exclude(city_town='')
                    .values_list('city_town', flat=True)
                    .distinct()[:10]
                ),
            }
            cache.set(cache_key, cached_payload, self.cache_ttl_seconds)

        context['upcoming_listings'] = self._ordered_listings_from_ids(cached_payload['upcoming_ids'])
        context['recent_listings'] = self._ordered_listings_from_ids(cached_payload['recent_ids'])
        context['popular_sports'] = cached_payload['popular_sports']
        context['popular_towns'] = cached_payload['popular_towns']
        return context

    def _cache_version(self):
        latest_updated = Listing.objects.aggregate(latest=Max('updated_at')).get('latest')
        if not latest_updated:
            return '0'
        return latest_updated.strftime('%Y%m%d%H%M%S%f')


class ListingListView(ListView):
    model = Listing
    template_name = 'core/listing_list.html'
    context_object_name = 'listings'
    paginate_by = 24
    category = None
    page_title = 'Listings'
    section_slug = ''
    cache_ttl_seconds = 300

    def get_base_queryset(self):
        queryset = Listing.objects.filter(status=Listing.Status.PUBLISHED)
        if self.category:
            queryset = queryset.filter(category=self.category)
        return queryset

    def get_queryset(self):
        queryset = self.get_base_queryset()

        search = self.request.GET.get('q', '').strip()
        subtype = self.get_requested_subtype(queryset)
        city_town = self.get_requested_city_town(queryset, subtype)
        gender = self.request.GET.get('gender', '').strip()
        age = self.request.GET.get('age', '').strip()
        sort = self.request.GET.get('sort', '').strip()

        if subtype:
            queryset = queryset.filter(subtype__iexact=subtype)
        if city_town:
            queryset = queryset.filter(city_town__iexact=city_town)
        if gender:
            queryset = queryset.filter(gender=gender)
        if age.isdigit():
            age_value = int(age)
            queryset = queryset.filter(age_min__lte=age_value, age_max__gte=age_value)

        if search:
            exact_matches = queryset.filter(
                Q(title__icontains=search)
                | Q(subtype__icontains=search)
                | Q(organization_name__icontains=search)
                | Q(description__icontains=search)
                | Q(city_town__icontains=search)
            )
            fuzzy_ids = self._fuzzy_match_ids(queryset, search)
            if fuzzy_ids:
                queryset = queryset.filter(Q(id__in=fuzzy_ids) | Q(id__in=exact_matches.values('id')))
            else:
                queryset = exact_matches

        queryset = self._apply_sort(queryset, sort)
        cache_key = self._build_results_cache_key(subtype=subtype, city_town=city_town)
        cached_ids = cache.get(cache_key)
        if cached_ids is None:
            cached_ids = list(queryset.values_list('id', flat=True))
            cache.set(cache_key, cached_ids, self.cache_ttl_seconds)
        return self._ordered_queryset_from_ids(cached_ids)

    def get_requested_subtype(self, base_queryset):
        subtype_slug = self.kwargs.get('subtype_slug')
        if subtype_slug:
            return self._resolve_value_from_slug(base_queryset, 'subtype', subtype_slug)
        return self.request.GET.get('subtype', '').strip()

    def get_requested_city_town(self, base_queryset, subtype):
        city_slug = self.kwargs.get('city_slug')
        if city_slug:
            scoped = base_queryset
            if subtype:
                scoped = scoped.filter(subtype__iexact=subtype)
            return self._resolve_value_from_slug(scoped, 'city_town', city_slug)
        return self.request.GET.get('city_town', '').strip()

    def _resolve_value_from_slug(self, queryset, field_name, slug_value):
        values = queryset.exclude(**{field_name: ''}).values_list(field_name, flat=True).distinct()
        for value in values:
            if slugify(value) == slug_value:
                return value
        return slug_value.replace('-', ' ').strip()

    def _fuzzy_match_ids(self, queryset, search):
        query_text = search.lower().strip()
        if len(query_text) < 3:
            return []

        matched_ids = []
        for row in queryset.values('id', 'title', 'subtype', 'organization_name', 'city_town'):
            candidates = [
                (row.get('title') or '').lower(),
                (row.get('subtype') or '').lower(),
                (row.get('organization_name') or '').lower(),
                (row.get('city_town') or '').lower(),
            ]
            score = max((SequenceMatcher(None, query_text, c).ratio() for c in candidates if c), default=0)
            if score >= 0.72:
                matched_ids.append(row['id'])
        return matched_ids

    def _apply_sort(self, queryset, sort):
        if sort == 'recent':
            return queryset.order_by('-created_at')
        if sort == 'age_asc':
            return queryset.order_by('age_min', 'age_max', 'title')
        return queryset.order_by(F('start_date').asc(nulls_last=True), 'title')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = self.get_base_queryset()
        subtype = self.get_requested_subtype(base_queryset)
        city_town = self.get_requested_city_town(base_queryset, subtype)

        page_title = self.page_title
        if subtype:
            label = 'Youth' if self.category == Listing.Category.SPORT else ''
            if city_town:
                page_title = f'{city_town} {label} {subtype}'.strip()
            else:
                page_title = f'{label} {subtype}'.strip()

        city_queryset = base_queryset
        if subtype:
            city_queryset = city_queryset.filter(subtype__iexact=subtype)

        context['page_title'] = page_title
        context['city_options'] = (
            city_queryset
            .order_by('city_town')
            .values_list('city_town', flat=True)
            .distinct()
        )
        context['subtype_options'] = (
            self.get_base_queryset()
            .order_by('subtype')
            .values_list('subtype', flat=True)
            .distinct()
        )
        context['gender_options'] = Listing.Gender.choices
        context['current_filters'] = {
            'q': self.request.GET.get('q', '').strip(),
            'city_town': city_town,
            'gender': self.request.GET.get('gender', '').strip(),
            'age': self.request.GET.get('age', '').strip(),
            'subtype': subtype,
            'sort': self.request.GET.get('sort', '').strip(),
        }
        context['sort_options'] = [
            ('soonest', 'Soonest start'),
            ('recent', 'Recently added'),
            ('age_asc', 'Ages low-high'),
        ]
        context['active_section'] = self.category
        context['canonical_url'] = self.request.build_absolute_uri(self._canonical_path(subtype, city_town))
        context['seo_json_ld'] = self._build_list_json_ld(page_title, context['listings'])
        context['sports_subtype_links'] = self._build_subtype_links(Listing.Category.SPORT)
        context['activities_subtype_links'] = self._build_subtype_links(Listing.Category.ACTIVITY)
        result_count = context['paginator'].count if context.get('paginator') else len(context['listings'])
        self._record_search_analytics(subtype=subtype, city_town=city_town, result_count=result_count)
        return context

    def _canonical_path(self, subtype, city_town):
        if self.category == Listing.Category.SPORT:
            if subtype and city_town:
                return reverse(
                    'core:sports_subtype_city',
                    kwargs={'subtype_slug': slugify(subtype), 'city_slug': slugify(city_town)},
                )
            if subtype:
                return reverse('core:sports_subtype', kwargs={'subtype_slug': slugify(subtype)})
            return reverse('core:sports')
        if self.category == Listing.Category.ACTIVITY:
            if subtype and city_town:
                return reverse(
                    'core:activities_subtype_city',
                    kwargs={'subtype_slug': slugify(subtype), 'city_slug': slugify(city_town)},
                )
            if subtype:
                return reverse(
                    'core:activities_subtype', kwargs={'subtype_slug': slugify(subtype)}
                )
            return reverse('core:activities')
        return self.request.path

    def _build_list_json_ld(self, page_title, listings):
        items = []
        for index, listing in enumerate(list(listings)[:20], start=1):
            items.append(
                {
                    '@type': 'ListItem',
                    'position': index,
                    'url': self.request.build_absolute_uri(
                        reverse('core:listing_detail', kwargs={'pk': listing.pk})
                    ),
                    'name': listing.title,
                }
            )
        data = {
            '@context': 'https://schema.org',
            '@type': 'ItemList',
            'name': page_title,
            'numberOfItems': len(items),
            'itemListElement': items,
        }
        return json.dumps(data)

    def _build_subtype_links(self, category):
        subtype_values = (
            Listing.objects.filter(status=Listing.Status.PUBLISHED, category=category)
            .exclude(subtype='')
            .order_by('subtype')
            .values_list('subtype', flat=True)
            .distinct()
        )
        links = []
        for subtype_value in subtype_values:
            if category == Listing.Category.SPORT:
                path = reverse(
                    'core:sports_subtype', kwargs={'subtype_slug': slugify(subtype_value)}
                )
            else:
                path = reverse(
                    'core:activities_subtype', kwargs={'subtype_slug': slugify(subtype_value)}
                )
            links.append({'name': subtype_value, 'path': path})
        return links

    def _build_results_cache_key(self, subtype, city_town):
        cache_version = self._cache_version()
        return ':'.join(
            [
                'listing-list',
                cache_version,
                self.category or 'all',
                subtype.lower() if subtype else 'all-subtypes',
                city_town.lower() if city_town else 'all-cities',
                (self.request.GET.get('q', '').strip().lower() or 'no-q'),
                (self.request.GET.get('gender', '').strip().lower() or 'any-gender'),
                (self.request.GET.get('age', '').strip() or 'any-age'),
                (self.request.GET.get('sort', '').strip().lower() or 'soonest'),
            ]
        )

    def _cache_version(self):
        queryset = Listing.objects.filter(status=Listing.Status.PUBLISHED)
        if self.category:
            queryset = queryset.filter(category=self.category)
        latest_updated = queryset.aggregate(latest=Max('updated_at')).get('latest')
        if not latest_updated:
            return '0'
        return latest_updated.strftime('%Y%m%d%H%M%S%f')

    def _ordered_queryset_from_ids(self, ids):
        if not ids:
            return Listing.objects.none()
        ordering = Case(
            *[When(pk=pk, then=pos) for pos, pk in enumerate(ids)],
            output_field=IntegerField(),
        )
        return Listing.objects.filter(pk__in=ids).order_by(ordering)

    def _record_search_analytics(self, subtype, city_town, result_count):
        query = self.request.GET.get('q', '').strip()
        page_value = self.request.GET.get('page', '1').strip() or '1'
        if not query or page_value != '1':
            return
        base_payload = {
            'event_type': ListingAnalyticsEvent.EventType.SEARCH,
            'section': self.category or '',
            'query': query[:255],
            'subtype': (subtype or '')[:120],
            'city_town': (city_town or '')[:120],
            'result_count': result_count,
        }
        ListingAnalyticsEvent.objects.create(**base_payload)
        if result_count == 0:
            ListingAnalyticsEvent.objects.create(
                event_type=ListingAnalyticsEvent.EventType.EMPTY_SEARCH,
                section=self.category or '',
                query=query[:255],
                subtype=(subtype or '')[:120],
                city_town=(city_town or '')[:120],
                result_count=0,
            )


class SportsListView(ListingListView):
    category = Listing.Category.SPORT
    page_title = 'Sports'
    section_slug = 'sports'


class ActivitiesListView(ListingListView):
    category = Listing.Category.ACTIVITY
    page_title = 'Activities'
    section_slug = 'activities'


class SportsSubtypeListView(SportsListView):
    pass


class SportsSubtypeCityListView(SportsListView):
    pass


class ActivitiesSubtypeListView(ActivitiesListView):
    pass


class ActivitiesSubtypeCityListView(ActivitiesListView):
    pass


class OutboundListingRedirectView(View):
    def get(self, request, *args, **kwargs):
        listing = get_object_or_404(Listing, pk=kwargs['pk'], status=Listing.Status.PUBLISHED)
        section = ''
        referer = request.META.get('HTTP_REFERER', '')
        if '/sports' in referer:
            section = Listing.Category.SPORT
        elif '/activities' in referer:
            section = Listing.Category.ACTIVITY
        ListingAnalyticsEvent.objects.create(
            event_type=ListingAnalyticsEvent.EventType.OUTBOUND_CLICK,
            listing=listing,
            section=section,
            subtype=listing.subtype[:120],
            city_town=listing.city_town[:120],
            target_url=listing.registration_url,
        )
        return HttpResponseRedirect(listing.registration_url)


class SitemapXmlView(View):
    def get(self, request, *args, **kwargs):
        urls = [
            request.build_absolute_uri(reverse('core:home')),
            request.build_absolute_uri(reverse('core:sports')),
            request.build_absolute_uri(reverse('core:activities')),
            request.build_absolute_uri(reverse('core:resources')),
            request.build_absolute_uri(reverse('core:contact')),
            request.build_absolute_uri(reverse('core:suggest_listing')),
        ]

        for subtype in (
            Listing.objects.filter(status=Listing.Status.PUBLISHED, category=Listing.Category.SPORT)
            .exclude(subtype='')
            .values_list('subtype', flat=True)
            .distinct()
        ):
            urls.append(
                request.build_absolute_uri(
                    reverse('core:sports_subtype', kwargs={'subtype_slug': slugify(subtype)})
                )
            )

        for subtype in (
            Listing.objects.filter(status=Listing.Status.PUBLISHED, category=Listing.Category.ACTIVITY)
            .exclude(subtype='')
            .values_list('subtype', flat=True)
            .distinct()
        ):
            urls.append(
                request.build_absolute_uri(
                    reverse('core:activities_subtype', kwargs={'subtype_slug': slugify(subtype)})
                )
            )

        listing_entries = Listing.objects.filter(status=Listing.Status.PUBLISHED).values(
            'id', 'updated_at'
        )

        lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for url in urls:
            lines.extend(
                [
                    '  <url>',
                    f'    <loc>{escape(url)}</loc>',
                    '  </url>',
                ]
            )
        for entry in listing_entries:
            lines.extend(
                [
                    '  <url>',
                    f"    <loc>{escape(request.build_absolute_uri(reverse('core:listing_detail', kwargs={'pk': entry['id']})))}</loc>",
                    f"    <lastmod>{entry['updated_at'].date().isoformat()}</lastmod>",
                    '  </url>',
                ]
            )
        lines.append('</urlset>')
        return HttpResponse('\n'.join(lines), content_type='application/xml')


class RobotsTxtView(View):
    def get(self, request, *args, **kwargs):
        content = '\n'.join(
            [
                'User-agent: *',
                'Allow: /',
                f'Sitemap: {request.build_absolute_uri(reverse("core:sitemap_xml"))}',
            ]
        )
        return HttpResponse(content, content_type='text/plain')


class ListingDetailView(DetailView):
    model = Listing
    template_name = 'core/listing_detail.html'
    context_object_name = 'listing'

    def get_queryset(self):
        return Listing.objects.filter(status=Listing.Status.PUBLISHED)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        listing = self.object
        context['is_stale'] = listing.is_stale
        context['report_form'] = kwargs.get('report_form') or OutdatedListingReportForm()
        context['canonical_url'] = self.request.build_absolute_uri(
            reverse('core:listing_detail', kwargs={'pk': listing.pk})
        )
        if listing.image:
            context['og_image_url'] = self.request.build_absolute_uri(listing.image.url)
        if self.request.user.is_staff:
            context['change_logs'] = listing.change_logs.select_related('actor').all()[:20]
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = OutdatedListingReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.listing = self.object
            report.save()
            messages.success(
                request,
                'Thanks. We received your report and will review this listing.',
            )
            return redirect('core:listing_detail', pk=self.object.pk)

        context = self.get_context_data(report_form=form)
        return self.render_to_response(context)


class ResourcesView(TemplateView):
    template_name = 'core/resources.html'


class ContactView(TemplateView):
    template_name = 'core/contact.html'


class SuggestListingView(FormView):
    template_name = 'core/suggest_listing.html'
    form_class = SuggestListingForm
    success_url = reverse_lazy('core:suggest_listing')

    def form_valid(self, form):
        suggestion = form.save_suggestion()
        messages.success(
            self.request,
            f'Thanks. Your suggestion for "{suggestion.title}" was submitted for staff review.',
        )
        return super().form_valid(form)


class AddNewListingView(StaffRequiredMixin, FormView):
    template_name = 'core/add_new_listing.html'
    form_class = AddNewListingForm
    success_url = reverse_lazy('core:add_new_listing')

    def form_valid(self, form):
        listing = form.save(user=self.request.user)
        ListingChangeLog.objects.create(
            listing=listing,
            actor=self.request.user,
            action=ListingChangeLog.Action.CREATED,
            notes='Created via Add New form.',
        )
        messages.success(
            self.request,
            f'Listing created as draft: {listing.title}. Publish it from the verification queue.',
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sport_type_count'] = SportType.objects.count()
        context['activity_type_count'] = ActivityType.objects.count()
        context['is_edit'] = False
        return context


class EditListingView(StaffRequiredMixin, FormView):
    template_name = 'core/add_new_listing.html'
    form_class = AddNewListingForm

    def dispatch(self, request, *args, **kwargs):
        self.listing = get_object_or_404(Listing, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        listing = self.listing
        return {
            'listing_type': listing.category,
            'state': listing.state_id,
            'county': listing.county_id,
            'city_town_ref': listing.city_town_ref_id,
            'city_town_manual': '' if listing.city_town_ref_id else listing.city_town,
            'sport_type': listing.sport_type_id,
            'custom_sport': listing.subtype if listing.category == Listing.Category.SPORT and not listing.sport_type_id else '',
            'activity_type': listing.activity_type_id,
            'custom_activity': listing.subtype if listing.category == Listing.Category.ACTIVITY and not listing.activity_type_id else '',
            'title': listing.title,
            'organization_name': listing.organization_name,
            'location_name': listing.location_name,
            'address': listing.address,
            'age_min': listing.age_min,
            'age_max': listing.age_max,
            'gender': listing.gender,
            'season_or_dates': listing.season_or_dates,
            'description': listing.description,
            'registration_url': listing.registration_url,
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.listing
        return kwargs

    def form_valid(self, form):
        changed_fields = self._compute_changed_fields(form.cleaned_data)
        listing = form.save(instance=self.listing, user=self.request.user)
        if changed_fields:
            ListingChangeLog.objects.create(
                listing=listing,
                actor=self.request.user,
                action=ListingChangeLog.Action.EDITED,
                changed_fields=changed_fields,
                notes='Edited via staff form.',
            )
        messages.success(
            self.request,
            f'Listing updated and saved as draft: {listing.title}. Publish it from the verification queue.',
        )
        return redirect('core:edit_listing', pk=listing.pk)

    def _compute_changed_fields(self, cleaned_data):
        listing = self.listing
        proposed_city_town = (
            cleaned_data['city_town_ref'].name
            if cleaned_data.get('city_town_ref')
            else cleaned_data.get('city_town_manual', '').strip()
        )
        proposed_subtype = ''
        if cleaned_data.get('listing_type') == Listing.Category.SPORT:
            proposed_subtype = (
                cleaned_data['sport_type'].name
                if cleaned_data.get('sport_type')
                else cleaned_data.get('custom_sport', '').strip()
            )
        else:
            proposed_subtype = (
                cleaned_data['activity_type'].name
                if cleaned_data.get('activity_type')
                else cleaned_data.get('custom_activity', '').strip()
            )

        comparisons = {
            'title': (listing.title, (cleaned_data.get('title') or '').strip() or f'{proposed_city_town} Youth {proposed_subtype}'),
            'category': (listing.category, cleaned_data.get('listing_type')),
            'subtype': (listing.subtype, proposed_subtype),
            'organization_name': (listing.organization_name, cleaned_data.get('organization_name')),
            'state_id': (listing.state_id, cleaned_data['state'].id if cleaned_data.get('state') else None),
            'county_id': (listing.county_id, cleaned_data['county'].id if cleaned_data.get('county') else None),
            'city_town_ref_id': (listing.city_town_ref_id, cleaned_data['city_town_ref'].id if cleaned_data.get('city_town_ref') else None),
            'city_town': (listing.city_town, proposed_city_town),
            'location_name': (listing.location_name, cleaned_data.get('location_name')),
            'address': (listing.address, (cleaned_data.get('address') or '').strip()),
            'age_min': (listing.age_min, cleaned_data.get('age_min')),
            'age_max': (listing.age_max, cleaned_data.get('age_max')),
            'gender': (listing.gender, cleaned_data.get('gender')),
            'season_or_dates': (listing.season_or_dates, cleaned_data.get('season_or_dates')),
            'registration_url': (listing.registration_url, cleaned_data.get('registration_url')),
            'description': (listing.description, cleaned_data.get('description')),
        }
        changed = [field for field, (old, new) in comparisons.items() if old != new]
        if cleaned_data.get('image'):
            changed.append('image')
        changed.append('status')
        return sorted(set(changed))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sport_type_count'] = SportType.objects.count()
        context['activity_type_count'] = ActivityType.objects.count()
        context['is_edit'] = True
        context['editing_listing'] = self.listing
        return context


class CountiesByStateView(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        state_id = request.GET.get('state_id')
        queryset = County.objects.none()
        if state_id and state_id.isdigit():
            queryset = County.objects.filter(state_id=int(state_id)).order_by('name')
        data = [{'id': county.id, 'name': county.name} for county in queryset]
        return JsonResponse({'results': data})


class CitiesByCountyView(StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        county_id = request.GET.get('county_id')
        queryset = CityTown.objects.none()
        if county_id and county_id.isdigit():
            queryset = CityTown.objects.filter(county_id=int(county_id)).order_by('name')
        data = [{'id': city.id, 'name': city.name} for city in queryset]
        return JsonResponse({'results': data})


class PublicCountiesByStateView(View):
    def get(self, request, *args, **kwargs):
        state_id = request.GET.get('state_id')
        queryset = County.objects.none()
        if state_id and state_id.isdigit():
            queryset = County.objects.filter(state_id=int(state_id)).order_by('name')
        data = [{'id': county.id, 'name': county.name} for county in queryset]
        return JsonResponse({'results': data})


class PublicCitiesByCountyView(View):
    def get(self, request, *args, **kwargs):
        county_id = request.GET.get('county_id')
        queryset = CityTown.objects.none()
        if county_id and county_id.isdigit():
            queryset = CityTown.objects.filter(county_id=int(county_id)).order_by('name')
        data = [{'id': city.id, 'name': city.name} for city in queryset]
        return JsonResponse({'results': data})


class VerificationQueueView(StaffRequiredMixin, TemplateView):
    template_name = 'core/verification_queue.html'
    per_page = 10

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        snapshot_at = timezone.now()
        stale_threshold = timezone.now() - timezone.timedelta(days=90)
        town = self.request.GET.get('town', '').strip()
        sport = self.request.GET.get('sport', '').strip()
        has_reports = self.request.GET.get('has_reports') == '1'
        stale_only = self.request.GET.get('stale_only') == '1'

        unresolved_report_listing_ids = list(
            ListingOutdatedReport.objects.filter(resolved=False).values_list('listing_id', flat=True)
        )

        stale_queryset = Listing.objects.filter(
            status=Listing.Status.PUBLISHED,
            last_verified_at__lt=stale_threshold,
        )
        draft_queryset = Listing.objects.filter(status=Listing.Status.DRAFT)
        reports_queryset = ListingOutdatedReport.objects.filter(resolved=False).select_related(
            'listing'
        )

        if town:
            stale_queryset = stale_queryset.filter(city_town__iexact=town)
            draft_queryset = draft_queryset.filter(city_town__iexact=town)
            reports_queryset = reports_queryset.filter(listing__city_town__iexact=town)
        if sport:
            stale_queryset = stale_queryset.filter(subtype__iexact=sport)
            draft_queryset = draft_queryset.filter(subtype__iexact=sport)
            reports_queryset = reports_queryset.filter(listing__subtype__iexact=sport)
        if has_reports:
            stale_queryset = stale_queryset.filter(id__in=unresolved_report_listing_ids)
            draft_queryset = draft_queryset.filter(id__in=unresolved_report_listing_ids)
        if stale_only:
            reports_queryset = reports_queryset.filter(listing__last_verified_at__lt=stale_threshold)

        stale_queryset = stale_queryset.order_by('last_verified_at', 'title')
        draft_queryset = draft_queryset.order_by(
            '-updated_at', 'title'
        )
        reports_queryset = reports_queryset.order_by('-created_at')

        draft_page_obj = Paginator(draft_queryset, self.per_page).get_page(
            self.request.GET.get('draft_page', 1)
        )
        stale_page_obj = Paginator(stale_queryset, self.per_page).get_page(
            self.request.GET.get('stale_page', 1)
        )
        reports_page_obj = Paginator(reports_queryset, self.per_page).get_page(
            self.request.GET.get('reports_page', 1)
        )
        suggestions_queryset = ListingSuggestion.objects.filter(
            status=ListingSuggestion.Status.PENDING
        ).order_by('-created_at')
        if town:
            suggestions_queryset = suggestions_queryset.filter(city_town__iexact=town)
        if sport:
            suggestions_queryset = suggestions_queryset.filter(subtype__iexact=sport)
        suggestions_page_obj = Paginator(suggestions_queryset, self.per_page).get_page(
            self.request.GET.get('suggestions_page', 1)
        )

        context['draft_listings'] = draft_page_obj.object_list
        context['stale_listings'] = stale_page_obj.object_list
        context['open_reports'] = reports_page_obj.object_list
        context['pending_suggestions'] = suggestions_page_obj.object_list
        context['draft_page_obj'] = draft_page_obj
        context['stale_page_obj'] = stale_page_obj
        context['reports_page_obj'] = reports_page_obj
        context['suggestions_page_obj'] = suggestions_page_obj
        context['queue_filters'] = {
            'town': town,
            'sport': sport,
            'has_reports': has_reports,
            'stale_only': stale_only,
        }
        context['town_options'] = (
            Listing.objects.exclude(city_town='')
            .values_list('city_town', flat=True)
            .distinct()
            .order_by('city_town')
        )
        context['sport_options'] = (
            Listing.objects.exclude(subtype='')
            .values_list('subtype', flat=True)
            .distinct()
            .order_by('subtype')
        )
        context['queue_snapshot_generated_at'] = snapshot_at
        context['queue_summary'] = {
            'draft_count': draft_queryset.count(),
            'stale_count': stale_queryset.count(),
            'open_report_count': reports_queryset.count(),
            'pending_suggestion_count': suggestions_queryset.count(),
        }
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        report_id = request.POST.get('report_id')
        listing_id = request.POST.get('listing_id')
        suggestion_id = request.POST.get('suggestion_id')
        if action == 'resolve' and report_id and report_id.isdigit():
            report = get_object_or_404(ListingOutdatedReport, pk=int(report_id))
            report.resolved = True
            report.save(update_fields=['resolved'])
            messages.success(request, 'Report marked as resolved.')
        elif action == 'verify' and listing_id and listing_id.isdigit():
            listing = get_object_or_404(Listing, pk=int(listing_id))
            listing.last_verified_at = timezone.now()
            listing.updated_by = request.user
            listing.save(update_fields=['last_verified_at', 'updated_at', 'updated_by'])
            ListingChangeLog.objects.create(
                listing=listing,
                actor=request.user,
                action=ListingChangeLog.Action.EDITED,
                changed_fields=['last_verified_at'],
                notes='Marked verified today from verification queue.',
            )
            messages.success(request, f'Marked verified today: {listing.title}')
        elif action == 'publish' and listing_id and listing_id.isdigit():
            listing = get_object_or_404(Listing, pk=int(listing_id))
            listing.status = Listing.Status.PUBLISHED
            listing.updated_by = request.user
            listing.last_verified_at = timezone.now()
            listing.save(update_fields=['status', 'last_verified_at', 'updated_at', 'updated_by'])
            ListingChangeLog.objects.create(
                listing=listing,
                actor=request.user,
                action=ListingChangeLog.Action.PUBLISHED,
                changed_fields=['status', 'last_verified_at'],
                notes='Published from verification queue.',
            )
            messages.success(request, f'Published listing: {listing.title}')
        elif action == 'approve_suggestion' and suggestion_id and suggestion_id.isdigit():
            suggestion = get_object_or_404(ListingSuggestion, pk=int(suggestion_id))
            listing = Listing.objects.create(
                title=suggestion.title,
                category=suggestion.category,
                subtype=suggestion.subtype,
                sport_type=suggestion.sport_type,
                activity_type=suggestion.activity_type,
                organization_name=suggestion.organization_name,
                state=suggestion.state,
                county=suggestion.county,
                city_town_ref=suggestion.city_town_ref,
                city_town=suggestion.city_town,
                location_name=suggestion.location_name,
                address=suggestion.address,
                age_min=suggestion.age_min,
                age_max=suggestion.age_max,
                gender=suggestion.gender,
                season_or_dates=suggestion.season_or_dates,
                registration_url=suggestion.registration_url,
                image=suggestion.image,
                description=suggestion.description,
                status=Listing.Status.PUBLISHED,
                last_verified_at=timezone.now(),
                created_by=request.user,
                updated_by=request.user,
            )
            ListingChangeLog.objects.create(
                listing=listing,
                actor=request.user,
                action=ListingChangeLog.Action.CREATED,
                notes='Created by approving public suggestion.',
            )
            ListingChangeLog.objects.create(
                listing=listing,
                actor=request.user,
                action=ListingChangeLog.Action.PUBLISHED,
                changed_fields=['status', 'last_verified_at'],
                notes='Auto-published from approved public suggestion.',
            )
            suggestion.status = ListingSuggestion.Status.APPROVED
            suggestion.approved_listing = listing
            suggestion.reviewed_by = request.user
            suggestion.reviewed_at = timezone.now()
            suggestion.save(
                update_fields=['status', 'approved_listing', 'reviewed_by', 'reviewed_at']
            )
            messages.success(request, f'Approved suggestion and published: {listing.title}')
        elif action == 'reject_suggestion' and suggestion_id and suggestion_id.isdigit():
            suggestion = get_object_or_404(ListingSuggestion, pk=int(suggestion_id))
            suggestion.status = ListingSuggestion.Status.REJECTED
            suggestion.reviewed_by = request.user
            suggestion.reviewed_at = timezone.now()
            suggestion.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
            messages.success(request, f'Rejected suggestion: {suggestion.title}')
        return redirect('core:verification_queue')
