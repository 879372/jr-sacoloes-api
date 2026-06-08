from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
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


from django.db import transaction
from datetime import date
from dateutil.relativedelta import relativedelta

class ContaPagarViewSet(viewsets.ModelViewSet):
    queryset = ContaPagar.objects.all().select_related('categoria')
    pagination_class = None
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['descricao', 'fornecedor']
    ordering_fields = ['vencimento', 'valor', 'status']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ContaPagarReadSerializer
        return ContaPagarSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            conta = serializer.save()
            if conta.recorrente and conta.data_fim_recorrencia:
                current_venc = conta.vencimento
                parcela = 1
                while True:
                    current_venc = current_venc + relativedelta(months=1)
                    if current_venc > conta.data_fim_recorrencia:
                        break
                    parcela += 1
                    ContaPagar.objects.create(
                        descricao=f"{conta.descricao} ({parcela})",
                        fornecedor=conta.fornecedor,
                        categoria=conta.categoria,
                        valor=conta.valor,
                        vencimento=current_venc,
                        status='PENDENTE',
                        recorrente=True,
                        data_fim_recorrencia=conta.data_fim_recorrencia,
                        parcela_atual=parcela,
                        conta=conta.conta,
                    )

    @action(detail=True, methods=['post'])
    def transferir_conta(self, request, pk=None):
        """Transfere TODOS os lançamentos com a mesma descrição para outra conta (EMPRESA/PESSOAL)."""
        nova_conta = request.data.get('conta')
        if nova_conta not in ('EMPRESA', 'PESSOAL'):
            return Response({'erro': 'Conta inválida. Use EMPRESA ou PESSOAL.'}, status=400)

        item = self.get_object()
        # Busca pela raiz do nome (sem sufixo de parcela como " (2)", " (3)", ...)
        descricao_base = item.descricao.split(' (')[0]

        atualizado = ContaPagar.objects.filter(
            descricao__startswith=descricao_base
        ).update(conta=nova_conta)

        return Response({'atualizado': atualizado, 'conta': nova_conta})


class ContaReceberViewSet(viewsets.ModelViewSet):
    queryset = ContaReceber.objects.all().select_related('categoria')
    pagination_class = None
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['descricao', 'cliente_nome']
    ordering_fields = ['vencimento', 'valor', 'status']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ContaReceberReadSerializer
        return ContaReceberSerializer

    def perform_create(self, serializer):
        with transaction.atomic():
            conta = serializer.save()
            if conta.recorrente and conta.data_fim_recorrencia:
                current_venc = conta.vencimento
                parcela = 1
                while True:
                    current_venc = current_venc + relativedelta(months=1)
                    if current_venc > conta.data_fim_recorrencia:
                        break
                    parcela += 1
                    ContaReceber.objects.create(
                        descricao=f"{conta.descricao} ({parcela})",
                        cliente_nome=conta.cliente_nome,
                        categoria=conta.categoria,
                        valor=conta.valor,
                        vencimento=current_venc,
                        status='PENDENTE',
                        recorrente=True,
                        data_fim_recorrencia=conta.data_fim_recorrencia,
                        parcela_atual=parcela,
                        conta=conta.conta,
                    )

    @action(detail=True, methods=['post'])
    def transferir_conta(self, request, pk=None):
        """Transfere TODOS os lançamentos com a mesma descrição para outra conta (EMPRESA/PESSOAL)."""
        nova_conta = request.data.get('conta')
        if nova_conta not in ('EMPRESA', 'PESSOAL'):
            return Response({'erro': 'Conta inválida. Use EMPRESA ou PESSOAL.'}, status=400)

        item = self.get_object()
        descricao_base = item.descricao.split(' (')[0]

        atualizado = ContaReceber.objects.filter(
            descricao__startswith=descricao_base
        ).update(conta=nova_conta)

        return Response({'atualizado': atualizado, 'conta': nova_conta})

