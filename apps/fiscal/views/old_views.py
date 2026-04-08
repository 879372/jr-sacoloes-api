from rest_framework import viewsets, filters
from ..models import NotaFiscalEmitida
from ..serializers.old_serializers import NotaFiscalEmitidaSerializer, NotaFiscalEmitidaReadSerializer


class NotaFiscalEmitidaViewSet(viewsets.ModelViewSet):
    queryset = NotaFiscalEmitida.objects.all().select_related('venda')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero', 'destinatario_nome', 'chave_acesso']
    ordering_fields = ['emitida_em', 'status', 'tipo']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return NotaFiscalEmitidaReadSerializer
        return NotaFiscalEmitidaSerializer
