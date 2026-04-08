from rest_framework import serializers
from apps.fiscal.models import NFe

class NFeSerializer(serializers.ModelSerializer):
    venda_total = serializers.DecimalField(source='venda.total', max_digits=10, decimal_places=2, read_only=True)
    cliente_nome = serializers.CharField(source='venda.cliente.nome', read_only=True)

    class Meta:
        model = NFe
        fields = '__all__'
        read_only_fields = (
            'ref', 'status', 'status_sefaz', 'mensagem_sefaz', 'chave_nfe', 
            'numero', 'serie', 'protocolo', 'caminho_xml', 'caminho_danfe', 
            'resposta_focusnfe', 'cancelado_em', 'tentativas_consulta', 
            'ultima_consulta_em'
        )

class NFeEmitirSerializer(serializers.Serializer):
    venda_id = serializers.IntegerField(required=True)
    natureza_operacao = serializers.CharField(required=False, default="Venda de mercadoria")

class NFeCancelarSerializer(serializers.Serializer):
    justificativa = serializers.CharField(min_length=15, max_length=255)

class NFeEmailSerializer(serializers.Serializer):
    emails = serializers.ListField(child=serializers.EmailField())
