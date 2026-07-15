from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import IsSalesStaff, outlet_location_ids

from .gateways.base import GatewayError
from .models import PaymentIntent
from .serializers import PaymentIntentCreateSerializer, PaymentIntentSerializer
from .services import get_gateway, verify_intent


class PaymentIntentViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    POST /payment-intents/            → create an intent and get the QR to show the customer
    GET  /payment-intents/{id}/verify/ → ask the gateway whether it has been paid

    Intents are never updated or deleted by a client: their status is the gateway's
    word, not anyone else's. PUT/PATCH/DELETE are structurally absent.
    """
    serializer_class = PaymentIntentSerializer
    permission_classes = [IsSalesStaff]

    def get_queryset(self):
        qs = PaymentIntent.objects.select_related('location').order_by('-created_at')
        user = self.request.user
        # A cashier only ever sees the money they themselves put on screen.
        if user.role == 'cashier':
            return qs.filter(created_by=user)
        loc_ids = outlet_location_ids(user)
        if loc_ids is not None:
            qs = qs.filter(location__in=loc_ids)
        return qs

    def create(self, request, *args, **kwargs):
        ser = PaymentIntentCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        intent = PaymentIntent.objects.create(
            gateway=data['gateway'],
            amount_paisa=data['amount_paisa'],
            location=data['fulfilled_location'],
            session=data.get('session'),
            created_by=request.user,
        )

        try:
            qr = get_gateway(intent.gateway).create_qr(intent)
        except GatewayError as exc:
            # The customer has not been shown anything, so nothing is owed. Fail the
            # intent rather than leaving it dangling as if it were awaiting payment.
            intent.status = 'failed'
            intent.failure_reason = str(exc)
            intent.save(update_fields=['status', 'failure_reason', 'updated_at'])
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        intent.qr_payload = qr.qr_string
        intent.raw_response = qr.raw
        intent.save(update_fields=['qr_payload', 'raw_response', 'updated_at'])

        return Response(PaymentIntentSerializer(intent).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], url_path='verify')
    def verify(self, request, pk=None):
        """
        Poll the gateway. Safe to call repeatedly — a verified or failed intent is
        terminal and is returned as-is rather than re-checked.
        """
        intent = self.get_object()
        try:
            intent = verify_intent(intent)
        except GatewayError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(PaymentIntentSerializer(intent).data)
