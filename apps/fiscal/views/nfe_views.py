# apps/fiscal/views/nfe_views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from apps.fiscal.models import NFe
from apps.fiscal.serializers.nfe_serializers import NFeSerializer, NFeEmitirSerializer, NFeCancelarSerializer, NFeEmailSerializer
from apps.fiscal.services.nfe_service import NFeService

class NFeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NFe.objects.all().order_by('-created_at')
    serializer_class = NFeSerializer

    @extend_schema(request=NFeEmitirSerializer)
    @action(detail=False, methods=['post'], url_path='emitir')
    def emitir(self, request):
        serializer = NFeEmitirSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = NFeService()
        try:
            nfe = service.emitir_from_venda(
                venda_id=serializer.validated_data['venda_id'],
                natureza_operacao=serializer.validated_data['natureza_operacao']
            )
            return Response(NFeSerializer(nfe).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='sincronizar')
    def sincronizar(self, request, pk=None):
        nfe = self.get_object()
        service = NFeService()
        try:
            nfe = service.sincronizar_status(nfe)
            return Response(NFeSerializer(nfe).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=NFeCancelarSerializer)
    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        nfe = self.get_object()
        serializer = NFeCancelarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = NFeService()
        try:
            nfe = service.cancelar(nfe, serializer.validated_data['justificativa'])
            return Response(NFeSerializer(nfe).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=NFeEmailSerializer)
    @action(detail=True, methods=['post'], url_path='enviar-email')
    def enviar_email(self, request, pk=None):
        nfe = self.get_object()
        serializer = NFeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        service = NFeService()
        try:
            sucesso = service.enviar_email(nfe, serializer.validated_data['emails'])
            return Response({'status': 'sucesso' if sucesso else 'erro'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(request=None)
    @action(detail=True, methods=['get'], url_path='preview-danfe')
    def preview_danfe(self, request, pk=None):
        nfe = self.get_object()
        service = NFeService()
        try:
            # Para o preview, Focus NFe espera o payload original
            pdf_content = service.gerar_danfe_preview(nfe.payload_enviado)
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="preview-{nfe.ref}.pdf"'
            return response
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], url_path='consultar')
    def consultar(self, request, pk=None):
        nfe = self.get_object()
        service = NFeService()
        try:
            resultado = service.consultar(nfe.ref)
            return Response(resultado)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
