from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import HealthCheckView

# Each app's router registers its own resource prefix (e.g. 'orders', 'invoices').
# All API routes live under /api/.
_api = [
    path('', include('apps.accounts.urls')),
    path('', include('apps.locations.urls')),
    path('', include('apps.partners.urls')),
    path('', include('apps.catalog.urls')),
    path('', include('apps.lots.urls')),
    path('', include('apps.processing.urls')),
    path('', include('apps.inventory.urls')),
    path('', include('apps.procurement.urls')),
    path('', include('apps.payments.urls')),
    path('', include('apps.sales.urls')),
    path('', include('apps.billing.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', HealthCheckView.as_view(), name='health'),
    path('api/', include(_api)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
