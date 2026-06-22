from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PriceViewSet, ProductViewSet

router = DefaultRouter()
router.register('products', ProductViewSet, basename='product')
router.register('prices', PriceViewSet, basename='price')

urlpatterns = [path('', include(router.urls))]
