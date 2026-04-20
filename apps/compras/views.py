from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from .models import NotaCompra
from .serializers import NotaCompraSerializer, NotaCompraReadSerializer
from apps.produtos.services import registrar_movimentacao


class NotaCompraViewSet(viewsets.ModelViewSet):
    queryset = NotaCompra.objects.all().prefetch_related('itens__produto')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero_nf', 'fornecedor', 'cnpj_fornecedor']
    ordering_fields = ['data_entrada', 'valor_total']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return NotaCompraReadSerializer
        return NotaCompraSerializer

    @action(detail=True, methods=['post'])
    def receber(self, request, pk=None):
        """Finaliza o recebimento da nota e atualiza o estoque"""
        nota = self.get_object()
        
        if nota.status == 'RECEBIDA':
            return Response({'erro': 'Esta nota já foi recebida.'}, status=400)
            
        if nota.status == 'CANCELADA':
            return Response({'erro': 'Esta nota está cancelada.'}, status=400)

        with transaction.atomic():
            for item in nota.itens.all():
                if item.produto:
                    registrar_movimentacao(
                        produto=item.produto,
                        tipo='ENTRADA',
                        quantidade=item.quantidade,
                        motivo='COMPRA',
                        observacoes=f"Recebimento NF {nota.numero_nf}"
                    )
            
            nota.status = 'RECEBIDA'
            nota.save()
            
        return Response({'status': 'Nota recebida e estoque atualizado.'})

