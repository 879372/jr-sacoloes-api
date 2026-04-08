# apps/fiscal/serializers/nfce_serializers.py
from rest_framework import serializers
from apps.fiscal.models import NFCe


class ItemNFCeSerializer(serializers.Serializer):
    numero_item = serializers.CharField()
    codigo_ncm = serializers.CharField()
    codigo_produto = serializers.CharField()
    descricao = serializers.CharField()
    quantidade_comercial = serializers.DecimalField(max_digits=15, decimal_places=4)
    quantidade_tributavel = serializers.DecimalField(max_digits=15, decimal_places=4)
    cfop = serializers.CharField(max_length=4)
    valor_unitario_comercial = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_unitario_tributavel = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_bruto = serializers.DecimalField(max_digits=15, decimal_places=2)
    valor_desconto = serializers.DecimalField(max_digits=15, decimal_places=2, default=0)
    unidade_comercial = serializers.CharField(max_length=6)
    unidade_tributavel = serializers.CharField(max_length=6)
    icms_origem = serializers.CharField(max_length=1)
    icms_situacao_tributaria = serializers.CharField(max_length=3)
    valor_total_tributos = serializers.DecimalField(max_digits=15, decimal_places=2, required=False)


class FormaPagamentoSerializer(serializers.Serializer):
    FORMA_CHOICES = [
        ("01", "Dinheiro"), ("02", "Cheque"), ("03", "Cartão de Crédito"),
        ("04", "Cartão de Débito"), ("05", "Crédito Loja"), ("10", "Vale Alimentação"),
        ("11", "Vale Refeição"), ("12", "Vale Presente"), ("13", "Vale Combustível"),
        ("99", "Outros"),
    ]
    forma_pagamento = serializers.ChoiceField(choices=FORMA_CHOICES)
    valor_pagamento = serializers.DecimalField(max_digits=15, decimal_places=2)
    tipo_integracao = serializers.CharField(required=False, allow_null=True)
    nome_credenciadora = serializers.CharField(required=False, allow_null=True)
    bandeira_operadora = serializers.CharField(required=False, allow_null=True)
    numero_autorizacao = serializers.CharField(required=False, allow_null=True)


class NFCeEmissaoSerializer(serializers.Serializer):
    data_emissao = serializers.DateTimeField()
    presenca_comprador = serializers.ChoiceField(
        choices=[("1", "Presencial"), ("4", "Entrega domicílio")], default="1"
    )
    modalidade_frete = serializers.ChoiceField(
        choices=[("0", "Emitente"), ("1", "Destinatário"), ("2", "Terceiros"), ("9", "Sem frete")],
        default="9",
    )
    local_destino = serializers.ChoiceField(
        choices=[("1", "Interna"), ("2", "Interestadual"), ("3", "Exterior")], default="1"
    )
    natureza_operacao = serializers.CharField(default="VENDA AO CONSUMIDOR")
    nome_destinatario = serializers.CharField(required=False, allow_null=True)
    cpf_destinatario = serializers.CharField(required=False, allow_null=True)
    cnpj_destinatario = serializers.CharField(required=False, allow_null=True)
    indicador_inscricao_estadual_destinatario = serializers.CharField(required=False, default="9")
    info_adicional = serializers.CharField(required=False, allow_null=True)
    items = ItemNFCeSerializer(many=True)
    formas_pagamento = FormaPagamentoSerializer(many=True)


class NFCeResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = NFCe
        fields = [
            "id", "ref", "status", "status_sefaz", "mensagem_sefaz",
            "chave_nfe", "numero", "serie", "protocolo",
            "caminho_xml", "caminho_danfe", "caminho_xml_cancelamento",
            "qrcode_url", "url_consulta_nf",
            "contingencia_offline", "contingencia_offline_efetivada",
            "created_at", "cancelado_em",
            "venda_total", "cliente_nome",
        ]

    venda_total = serializers.DecimalField(source="venda.total", max_digits=15, decimal_places=2, read_only=True)
    cliente_nome = serializers.CharField(source="venda.cliente.nome", default="Consumidor Final", read_only=True)


class NFCeCancelamentoSerializer(serializers.Serializer):
    justificativa = serializers.CharField(min_length=15, max_length=255)


class NFCeEmailSerializer(serializers.Serializer):
    emails = serializers.ListField(
        child=serializers.EmailField(),
        max_length=10,
        min_length=1,
    )


class NFCeInutilizacaoSerializer(serializers.Serializer):
    serie = serializers.CharField(max_length=3)
    numero_inicial = serializers.CharField()
    numero_final = serializers.CharField()
    justificativa = serializers.CharField(min_length=15, max_length=255)
