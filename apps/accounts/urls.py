from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import EverfreshTokenObtainPairSerializer
from .throttles import LoginUsernameThrottle
from .views import AuditLogViewSet, UserViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('audit-logs', AuditLogViewSet, basename='audit-log')


class EverfreshTokenObtainPairView(TokenObtainPairView):
    serializer_class = EverfreshTokenObtainPairSerializer
    # Brute-force guard: credential guessing is rate-limited per client IP *and*
    # per username (EF-09), so a shared NAT can't lock out an outlet and a single
    # account can't be sprayed from many IPs.
    throttle_scope = 'login'
    throttle_classes = [ScopedRateThrottle, LoginUsernameThrottle]


urlpatterns = [
    path('auth/token/', EverfreshTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('', include(router.urls)),
]
