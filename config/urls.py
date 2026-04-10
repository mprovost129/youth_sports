from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns

if settings.DEBUG or getattr(settings, 'SERVE_MEDIA', False):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
