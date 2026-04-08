# apps/fiscal/views/nfce_views.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.fiscal.models import NFCe
from apps.fiscal.services.nfce_service import NFCeService
from apps.fiscal.serializers.nfce_serializers import (
    NFCeEmissaoSerializer,
    NFCeResponseSerializer,
    NFCeCancelamentoSerializer,
    NFCeEmailSerializer,
    NFCeInutilizacaoSerializer,
)
import structlog

logger = structlog.get_logger()


class NFCeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NFCe.objects.all().order_by('-created_at')
    # Descomente ou mantenha conforme as politicas de autenticacao global
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        action_map = {
            "emitir": NFCeEmissaoSerializer,
            "cancelar": NFCeCancelamentoSerializer,
            "enviar_email": NFCeEmailSerializer,
            "inutilizar": NFCeInutilizacaoSerializer,
        }
        return action_map.get(self.action, NFCeResponseSerializer)

    @action(detail=False, methods=["post"], url_path="emitir")
    def emitir(self, request):
        """POST /api/v1/fiscal/nfce/emitir/"""
        serializer = NFCeEmissaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = NFCeService()
        nfce = service.emitir(serializer.validated_data)

        response_serializer = NFCeResponseSerializer(nfce)
        http_status = (
            status.HTTP_201_CREATED
            if nfce.foi_autorizada
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        return Response(response_serializer.data, status=http_status)

    @action(detail=False, methods=["get"], url_path="consultar/(?P<ref>[^/.]+)")
    def consultar(self, request, ref=None):
        """GET /api/v1/fiscal/nfce/consultar/{ref}/"""
        try:
            # TODO: validar se ref é None, mas regexp já previne na URL.
            pass
        except NFCe.DoesNotExist:
            pass

        try:
            # Em vez de requerer NFCe no DB para consulta remota, pode-se ir direto com a referência:
            nfce_db_exists = NFCe.objects.filter(ref=ref).exists()
            if not nfce_db_exists:
                return Response(
                    {"erro": "NFC-e não encontrada no sistema Antigravity."},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            completa = request.query_params.get("completa", "0") == "1"
            service = NFCeService()
            data = service.consultar(ref, completa=completa)
            return Response(data)
        except Exception as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], url_path="cancelar/(?P<ref>[^/.]+)")
    def cancelar(self, request, ref=None):
        """POST /api/v1/fiscal/nfce/cancelar/{ref}/"""
        try:
            nfce = NFCe.objects.get(ref=ref)
        except NFCe.DoesNotExist:
            return Response(
                {"erro": "NFC-e não encontrada."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = NFCeCancelamentoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = NFCeService()
        try:
            nfce = service.cancelar(nfce, serializer.validated_data["justificativa"])
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        return Response(NFCeResponseSerializer(nfce).data)

    @action(detail=False, methods=["post"], url_path="email/(?P<ref>[^/.]+)")
    def enviar_email(self, request, ref=None):
        """POST /api/v1/fiscal/nfce/email/{ref}/"""
        try:
            nfce = NFCe.objects.get(ref=ref)
        except NFCe.DoesNotExist:
            return Response(
                {"erro": "NFC-e não encontrada."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = NFCeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = NFCeService()
        try:
            service.enviar_email(nfce, serializer.validated_data["emails"])
        except ValueError as exc:
            return Response({"erro": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"mensagem": "Os emails serão enviados em breve."})

    @action(detail=False, methods=["post"], url_path="inutilizar")
    def inutilizar(self, request):
        """POST /api/v1/fiscal/nfce/inutilizar/"""
        serializer = NFCeInutilizacaoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = NFCeService()
        result = service.inutilizar(**serializer.validated_data)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="inutilizacoes")
    def listar_inutilizacoes(self, request):
        """GET /api/v1/fiscal/nfce/inutilizacoes/"""
        service = NFCeService()
        result = service.consultar_inutilizacoes(
            data_inicial=request.query_params.get("data_inicial"),
            data_final=request.query_params.get("data_final"),
            numero_inicial=request.query_params.get("numero_inicial"),
            numero_final=request.query_params.get("numero_final"),
        )
        return Response(result)
