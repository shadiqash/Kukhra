from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import GoodsReceivedViewSet, PurchaseOrderViewSet

router = DefaultRouter()
router.register('purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register('goods-received', GoodsReceivedViewSet, basename='goods-received')

urlpatterns = [path('', include(router.urls))]
