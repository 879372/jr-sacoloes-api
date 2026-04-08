from rest_framework import serializers
from .models import NotaCompra, ItemNotaCompra
from apps.produtos.serializers import ProdutoSimplificadoSerializer

class ItemNotaCompraSerializer(serializers.ModelSerializer):
    """Serializer para escrita de itens da nota de compra"""
    class Meta:
        model = ItemNotaCompra
        fields = ['id', 'produto', 'descricao', 'quantidade', 'valor_unitario', 'subtotal']


class ItemNotaCompraReadSerializer(ItemNotaCompraSerializer):
    """Serializer para leitura de itens com detalhes do produto"""
    produto = ProdutoSimplificadoSerializer(read_only=True)
    
    class Meta(ItemNotaCompraSerializer.Meta):
        fields = ItemNotaCompraSerializer.Meta.fields + ['created_at']


class NotaCompraSerializer(serializers.ModelSerializer):
    """Serializer para escrita de nota de compra, suportando itens aninhados"""
    itens = ItemNotaCompraSerializer(many=True, required=False)

    class Meta:
        model = NotaCompra
        fields = [
            'id', 'numero_nf', 'fornecedor', 'cnpj_fornecedor', 
            'data_emissao', 'data_entrada', 'valor_total', 
            'status', 'xml_nfe', 'chave_acesso', 'observacoes', 'itens'
        ]

    def create(self, validated_data):
        itens_data = validated_data.pop('itens', [])
        nota = NotaCompra.objects.create(**validated_data)
        for item_data in itens_data:
            ItemNotaCompra.objects.create(nota=nota, **item_data)
        return nota


class NotaCompraReadSerializer(NotaCompraSerializer):
    """Serializer detalhado para leitura de nota de compra"""
    itens = ItemNotaCompraReadSerializer(many=True, read_only=True)
    
    class Meta(NotaCompraSerializer.Meta):
        fields = NotaCompraSerializer.Meta.fields + ['itens', 'created_at', 'updated_at']
