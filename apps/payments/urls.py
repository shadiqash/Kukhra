from rest_framework.routers import DefaultRouter

from .views import PaymentIntentViewSet

router = DefaultRouter()
router.register('payment-intents', PaymentIntentViewSet, basename='payment-intent')

urlpatterns = router.urls
