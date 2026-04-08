from rest_framework import serializers
from .models import Produto, EstoqueLoja, MovimentacaoEstoque


class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimentacaoEstoque
        fields = ['id', 'tipo', 'motivo', 'quantidade', 'saldo_anterior', 'saldo_atual', 'observacoes', 'created_at']
        read_only_fields = ['id', 'created_at']


class EstoqueLojaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstoqueLoja
        fields = ['id', 'loja', 'quantidade', 'updated_at']


class ProdutoSerializer(serializers.ModelSerializer):
    """Serializer base para escrita (POST/PUT)"""
    class Meta:
        model = Produto
        fields = [
            'id', 'codigo_legado', 'nome', 'codigo_barras',
            'preco_compra', 'preco_venda', 'unidade_medida',
            'grupo', 'subgrupo', 'ativo',
            'ncm', 'cest', 'origem', 'cfop_padrao',
        ]


class ProdutoReadSerializer(ProdutoSerializer):
    """Serializer detalhado para leitura (GET) com estoques aninhados"""
    estoques = EstoqueLojaSerializer(many=True, read_only=True)

    class Meta(ProdutoSerializer.Meta):
        fields = ProdutoSerializer.Meta.fields + ['estoques', 'created_at', 'updated_at']


class ProdutoSimplificadoSerializer(serializers.ModelSerializer):
    """Versão leve para uso no PDV (busca rápida)"""
    class Meta:
        model = Produto
        fields = ['id', 'codigo_legado', 'nome', 'codigo_barras', 'preco_venda', 'unidade_medida']
