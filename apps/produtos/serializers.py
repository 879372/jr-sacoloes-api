from rest_framework import serializers
from .models import Produto, EstoqueLoja, MovimentacaoEstoque, Grupo


class GrupoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grupo
        fields = ['id', 'nome', 'descricao', 'ativo']
        read_only_fields = ['id']


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
    estoque_inicial = serializers.DecimalField(max_digits=15, decimal_places=3, required=False, write_only=True, default=0)

    class Meta:
        model = Produto
        fields = [
            'id', 'codigo_legado', 'nome', 'codigo_barras',
            'preco_compra', 'preco_venda', 'unidade_medida',
            'grupo', 'subgrupo', 'ativo',
            'ncm', 'cest', 'origem', 'cfop_padrao',
            'estoque_inicial'
        ]

    def create(self, validated_data):
        estoque_ini = validated_data.pop('estoque_inicial', 0)
        produto = super().create(validated_data)
        # Cria registro inicial de estoque
        if estoque_ini is not None:
            EstoqueLoja.objects.create(produto=produto, loja='Loja Principal', quantidade=estoque_ini)
            # Registra movimentação de ajuste inicial
            MovimentacaoEstoque.objects.create(
                produto=produto,
                tipo='ENTRADA',
                motivo='AJUSTE',
                quantidade=estoque_ini,
                saldo_anterior=0,
                saldo_atual=estoque_ini,
                observacoes='Ajuste de estoque inicial no cadastro do produto.'
            )
        return produto


class ProdutoReadSerializer(ProdutoSerializer):
    """Serializer detalhado para leitura (GET) com estoques aninhados"""
    estoques = EstoqueLojaSerializer(many=True, read_only=True)
    estoque_atual = serializers.SerializerMethodField()

    class Meta(ProdutoSerializer.Meta):
        fields = ProdutoSerializer.Meta.fields + ['estoques', 'estoque_atual', 'created_at', 'updated_at']

    def get_estoque_atual(self, obj):
        return sum(e.quantidade for e in obj.estoques.all())


class ProdutoSimplificadoSerializer(serializers.ModelSerializer):
    """Versão leve para uso no PDV (busca rápida)"""
    class Meta:
        model = Produto
        fields = ['id', 'codigo_legado', 'nome', 'codigo_barras', 'preco_venda', 'unidade_medida', 'ncm', 'cfop_padrao']
