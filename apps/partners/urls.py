from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CustomerViewSet, SupplierViewSet

router = DefaultRouter()
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('customers', CustomerViewSet, basename='customer')

urlpatterns = [path('', include(router.urls))]
