from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import LotViewSet

router = DefaultRouter()
router.register('lots', LotViewSet, basename='lot')

urlpatterns = [path('', include(router.urls))]
