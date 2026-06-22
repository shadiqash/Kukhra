from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CounterViewSet, LocationViewSet

router = DefaultRouter()
router.register('locations', LocationViewSet, basename='location')
router.register('counters', CounterViewSet, basename='counter')

urlpatterns = [path('', include(router.urls))]
