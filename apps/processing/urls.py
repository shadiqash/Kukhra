from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProcessingRunViewSet

router = DefaultRouter()
router.register('processing-runs', ProcessingRunViewSet, basename='processing-run')

urlpatterns = [path('', include(router.urls))]
