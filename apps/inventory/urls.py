from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import StockMovementViewSet, StockQueryView, StockTransferViewSet

router = DefaultRouter()
router.register('movements', StockMovementViewSet, basename='stock-movement')
router.register('transfers', StockTransferViewSet, basename='stock-transfer')
router.register('stock', StockQueryView, basename='stock-query')

urlpatterns = [path('', include(router.urls))]
