from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CashierSessionViewSet, OrderLineViewSet, OrderViewSet, PaymentViewSet

router = DefaultRouter()
router.register('sessions', CashierSessionViewSet, basename='cashier-session')
router.register('orders', OrderViewSet, basename='order')
router.register('order-lines', OrderLineViewSet, basename='order-line')
router.register('payments', PaymentViewSet, basename='payment')

urlpatterns = [path('', include(router.urls))]
