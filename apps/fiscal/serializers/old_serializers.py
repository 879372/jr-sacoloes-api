from rest_framework import serializers
from ..models import NotaFiscalEmitida


class NotaFiscalEmitidaSerializer(serializers.ModelSerializer):
    """Serializer para escrita de Nota Fiscal"""
    class Meta:
        model = NotaFiscalEmitida
        fields = [
            'id', 'venda', 'tipo', 'numero', 'chave_acesso', 
            'status', 'destinatario_nome', 'destinatario_cpf_cnpj', 
            'valor_total', 'emitida_em', 'enviado_contador', 
            'data_envio_contador', 'api_reference'
        ]


class NotaFiscalEmitidaReadSerializer(NotaFiscalEmitidaSerializer):
    """Serializer detalhado para leitura de Nota Fiscal"""
    venda_detalhes = serializers.ReadOnlyField(source='venda.id') # Simplificado por enquanto
    
    class Meta(NotaFiscalEmitidaSerializer.Meta):
        fields = NotaFiscalEmitidaSerializer.Meta.fields + ['venda_detalhes', 'created_at', 'updated_at']
