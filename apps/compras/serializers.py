from rest_framework import serializers, status
from django.db import transaction, IntegrityError
from rest_framework.validators import UniqueValidator
from .models import NotaCompra, ItemNotaCompra
from apps.produtos.serializers import ProdutoSimplificadoSerializer

class ItemNotaCompraSerializer(serializers.ModelSerializer):
    """Serializer para escrita de itens da nota de compra"""
    class Meta:
        model = ItemNotaCompra
        fields = ['id', 'produto', 'descricao', 'quantidade', 'valor_unitario', 'subtotal']
        read_only_fields = ['id']


class ItemNotaCompraReadSerializer(ItemNotaCompraSerializer):
    """Serializer para leitura de itens com detalhes do produto"""
    produto = ProdutoSimplificadoSerializer(read_only=True)
    
    class Meta(ItemNotaCompraSerializer.Meta):
        fields = ItemNotaCompraSerializer.Meta.fields + ['created_at']


class NotaCompraSerializer(serializers.ModelSerializer):
    """Serializer para escrita de nota de compra, suportando itens aninhados"""
    itens = ItemNotaCompraSerializer(many=True, required=False)
    
    # Custom validator to check unique chave_acesso even in soft-deleted records
    chave_acesso = serializers.CharField(
        validators=[UniqueValidator(queryset=NotaCompra.all_objects.all(), message="Esta nota fiscal (chave de acesso) já existe no sistema.")],
        required=False,
        allow_null=True,
        allow_blank=True
    )

    def validate_chave_acesso(self, value):
        """Converte strings vazias para None para evitar conflito de unicidade no DB"""
        if value == "" or value is None:
            return None
        return value

    def to_internal_value(self, data):
        """Pre-processamento para converter strings vazias em campos opcionais para None"""
        if 'chave_acesso' in data and data['chave_acesso'] == "":
            # Cria uma cópia mutável se necessário
            if hasattr(data, 'copy'):
                data = data.copy()
            data['chave_acesso'] = None
        return super().to_internal_value(data)

    class Meta:
        model = NotaCompra
        fields = [
            'id', 'numero_nf', 'fornecedor', 'cnpj_fornecedor', 
            'data_emissao', 'data_entrada', 'valor_total', 
            'status', 'xml_nfe', 'chave_acesso', 'observacoes', 'itens'
        ]
        read_only_fields = ['id', 'data_entrada']

    def create(self, validated_data):
        itens_data = validated_data.pop('itens', [])
        
        try:
            with transaction.atomic():
                nota = NotaCompra.objects.create(**validated_data)
                for item_data in itens_data:
                    ItemNotaCompra.objects.create(nota=nota, **item_data)
                return nota
        except IntegrityError as e:
            # Catch database level unique constraints just in case
            if 'chave_acesso' in str(e).lower():
                raise serializers.ValidationError({'chave_acesso': 'Esta nota fiscal já foi cadastrada (chave de acesso duplicada).'})
            raise serializers.ValidationError({'detail': f'Erro de integridade no banco de dados: {str(e)}'})
        except Exception as e:
            # Log or handle other errors that might cause 500
            raise serializers.ValidationError({'detail': f'Erro ao salvar nota de compra: {str(e)}'})


class NotaCompraReadSerializer(NotaCompraSerializer):
    """Serializer detalhado para leitura de nota de compra"""
    itens = ItemNotaCompraReadSerializer(many=True, read_only=True)
    
    class Meta(NotaCompraSerializer.Meta):
        fields = NotaCompraSerializer.Meta.fields + ['itens', 'created_at', 'updated_at']
