from rest_framework import serializers
from .models import ContaPagar, ContaReceber, CategoriaFinanceira


class CategoriaFinanceiraSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaFinanceira
        fields = ['id', 'nome', 'tipo']


class ContaPagarSerializer(serializers.ModelSerializer):
    """Serializer para escrita de contas a pagar"""
    class Meta:
        model = ContaPagar
        fields = [
            'id', 'descricao', 'fornecedor', 'categoria', 
            'valor', 'vencimento', 'data_pagamento', 
            'status', 'observacoes'
        ]


class ContaPagarReadSerializer(ContaPagarSerializer):
    """Serializer para leitura com detalhes da categoria"""
    categoria = CategoriaFinanceiraSerializer(read_only=True)
    
    class Meta(ContaPagarSerializer.Meta):
        fields = ContaPagarSerializer.Meta.fields + ['created_at', 'updated_at']


class ContaReceberSerializer(serializers.ModelSerializer):
    """Serializer para escrita de contas a receber"""
    class Meta:
        model = ContaReceber
        fields = [
            'id', 'descricao', 'cliente_nome', 'categoria', 
            'valor', 'vencimento', 'data_recebimento', 
            'status', 'observacoes'
        ]


class ContaReceberReadSerializer(ContaReceberSerializer):
    """Serializer para leitura com detalhes da categoria"""
    categoria = CategoriaFinanceiraSerializer(read_only=True)
    
    class Meta(ContaReceberSerializer.Meta):
        fields = ContaReceberSerializer.Meta.fields + ['created_at', 'updated_at']
