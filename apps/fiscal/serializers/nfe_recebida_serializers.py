from rest_framework import serializers
from apps.fiscal.models import NFeRecebida

class NFeRecebidaSerializer(serializers.ModelSerializer):
    manifestacao_display = serializers.CharField(source='get_manifestacao_destinatario_display', read_only=True)
    
    class Meta:
        model = NFeRecebida
        fields = [
            'id', 'chave_nfe', 'nome_emitente', 'documento_emitente',
            'valor_total', 'data_emissao', 'situacao', 
            'manifestacao_destinatario', 'manifestacao_display',
            'versao', 'nfe_completa', 'nota_compra', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
