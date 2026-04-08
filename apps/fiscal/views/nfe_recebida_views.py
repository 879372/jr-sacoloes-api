from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.fiscal.models import NFeRecebida
from apps.fiscal.serializers.nfe_recebida_serializers import NFeRecebidaSerializer
from apps.fiscal.services.manifesto_service import ManifestoService
from apps.compras.serializers import NotaCompraReadSerializer

class NFeRecebidaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NFeRecebida.objects.all()
    serializer_class = NFeRecebidaSerializer

    @action(detail=False, methods=['post'])
    def sincronizar(self, request):
        service = ManifestoService()
        try:
            result = service.sincronizar_notas()
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def manifestar_ciencia(self, request, pk=None):
        service = ManifestoService()
        try:
            success = service.manifestar_ciencia(pk)
            if success:
                return Response({'status': 'Ciência da operação registrada com sucesso.'})
            return Response({'error': 'Não foi possível registrar ciência.'}, status=400)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def importar(self, request, pk=None):
        service = ManifestoService()
        try:
            nota_compra = service.importar_para_compras(pk)
            return Response({
                'status': 'Nota de compra importada com sucesso.',
                'nota_compra': NotaCompraReadSerializer(nota_compra).data
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
