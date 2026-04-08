from rest_framework import viewsets, filters
from .models import ContaPagar, ContaReceber, CategoriaFinanceira
from .serializers import (
    ContaPagarSerializer, 
    ContaPagarReadSerializer,
    ContaReceberSerializer, 
    ContaReceberReadSerializer,
    CategoriaFinanceiraSerializer
)


class CategoriaFinanceiraViewSet(viewsets.ModelViewSet):
    queryset = CategoriaFinanceira.objects.all()
    serializer_class = CategoriaFinanceiraSerializer


class ContaPagarViewSet(viewsets.ModelViewSet):
    queryset = ContaPagar.objects.all().select_related('categoria')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['descricao', 'fornecedor']
    ordering_fields = ['vencimento', 'valor', 'status']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ContaPagarReadSerializer
        return ContaPagarSerializer


class ContaReceberViewSet(viewsets.ModelViewSet):
    queryset = ContaReceber.objects.all().select_related('categoria')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['descricao', 'cliente_nome']
    ordering_fields = ['vencimento', 'valor', 'status']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ContaReceberReadSerializer
        return ContaReceberSerializer
