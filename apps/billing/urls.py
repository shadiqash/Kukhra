from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CreditNoteViewSet, InvoiceLineViewSet, InvoiceViewSet

router = DefaultRouter()
router.register('invoices', InvoiceViewSet, basename='invoice')
router.register('invoice-lines', InvoiceLineViewSet, basename='invoice-line')
router.register('credit-notes', CreditNoteViewSet, basename='credit-note')

urlpatterns = [path('', include(router.urls))]
