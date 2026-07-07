"""
Operational endpoints — health checks for load balancers and container
orchestrators. Unauthenticated by design: they expose liveness only,
never business data.
"""
from django.conf import settings
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        checks = {'database': self._check_db(), 'redis': self._check_redis()}
        healthy = all(checks.values())
        return Response(
            {'status': 'ok' if healthy else 'degraded', 'checks': checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @staticmethod
    def _check_db():
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return True
        except Exception:
            return False

    @staticmethod
    def _check_redis():
        try:
            import redis

            client = redis.Redis.from_url(
                settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2
            )
            client.ping()
            return True
        except Exception:
            return False
