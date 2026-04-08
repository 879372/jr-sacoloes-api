from django.db import models
from apps.vendas.models import Venda
from apps.core.models import BaseModel, ActiveManager


class NotaFiscalEmitida(BaseModel):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EMITIDA', 'Emitida'),
        ('CANCELADA', 'Cancelada'),
        ('REJEITADA', 'Rejeitada'),
    ]
    TIPO_CHOICES = [('NFE', 'NF-e'), ('NFSE', 'NFS-e'), ('NFCE', 'NFC-e')]

    venda = models.ForeignKey(Venda, null=True, blank=True, on_delete=models.SET_NULL)
    tipo = models.CharField(max_length=5, choices=TIPO_CHOICES, default='NFE')
    numero = models.CharField(max_length=20, blank=True)
    chave_acesso = models.CharField(max_length=50, blank=True, null=True)
    xml = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    destinatario_nome = models.CharField(max_length=255, blank=True)
    destinatario_cpf_cnpj = models.CharField(max_length=20, blank=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Integração futura com Focus NFe
    api_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Referência da API Focus NFe")
    emitida_em = models.DateTimeField(null=True, blank=True)
    enviado_contador = models.BooleanField(default=False, help_text="XML enviado ao contador")
    data_envio_contador = models.DateTimeField(null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'fiscal'

    def __str__(self):
        return f"NF-e {self.numero or 'PENDENTE'} - {self.destinatario_nome}"


class NFCeStatus(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    AUTORIZADO = "autorizado", "Autorizado"
    ERRO_AUTORIZACAO = "erro_autorizacao", "Erro de Autorização"
    CANCELADO = "cancelado", "Cancelado"
    DENEGADO = "denegado", "Denegado"
    CONTINGENCIA = "contingencia", "Contingência Offline"


class NFeStatus(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    PROCESSANDO = "processando_autorizacao", "Processando Autorização"
    AUTORIZADO = "autorizado", "Autorizado"
    ERRO_AUTORIZACAO = "erro_autorizacao", "Erro de Autorização"
    CANCELADO = "cancelado", "Cancelado"
    DENEGADO = "denegado", "Denegado"


class NFCe(BaseModel):
    """
    Representa uma NFC-e emitida via Focus NFe.
    """

    ref = models.CharField(max_length=100, unique=True, db_index=True)
    chave_nfe = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    numero = models.CharField(max_length=10, blank=True, null=True)
    serie = models.CharField(max_length=5, blank=True, null=True)
    protocolo = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(
        max_length=30,
        choices=NFCeStatus.choices,
        default=NFCeStatus.PENDENTE,
    )
    status_sefaz = models.CharField(max_length=10, blank=True, null=True)
    mensagem_sefaz = models.TextField(blank=True, null=True)

    cnpj_emitente = models.CharField(max_length=14)

    caminho_xml = models.TextField(blank=True, null=True)
    caminho_danfe = models.TextField(blank=True, null=True)
    caminho_xml_cancelamento = models.TextField(blank=True, null=True)

    qrcode_url = models.TextField(blank=True, null=True)
    url_consulta_nf = models.TextField(blank=True, null=True)

    contingencia_offline = models.BooleanField(default=False)
    contingencia_offline_efetivada = models.BooleanField(default=False)

    payload_enviado = models.JSONField(null=True, blank=True)
    resposta_focusnfe = models.JSONField(null=True, blank=True)

    justificativa_cancelamento = models.TextField(blank=True, null=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)

    venda = models.ForeignKey(Venda, on_delete=models.PROTECT, null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "NFC-e"
        verbose_name_plural = "NFC-es"
        indexes = [
            models.Index(fields=["status", "is_deleted"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["cnpj_emitente", "status"]),
        ]

    def __str__(self):
        return f"NFC-e {self.numero or self.ref} [{self.status}]"

    @property
    def foi_autorizada(self) -> bool:
        return self.status == NFCeStatus.AUTORIZADO

    @property
    def pode_cancelar(self) -> bool:
        if self.status != NFCeStatus.AUTORIZADO:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at >= timezone.now() - timedelta(minutes=28)


class NFe(BaseModel):
    """
    Representa uma NF-e (Modelo 55) emitida via Focus NFe.
    Assíncrona: requer polling ou webhook para atualização de status.
    """
    ref = models.CharField(max_length=100, unique=True, db_index=True)
    chave_nfe = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    numero = models.CharField(max_length=10, blank=True, null=True)
    serie = models.CharField(max_length=5, blank=True, null=True)
    protocolo = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(
        max_length=30,
        choices=NFeStatus.choices,
        default=NFeStatus.PENDENTE,
        db_index=True,
    )
    status_sefaz = models.CharField(max_length=10, blank=True, null=True)
    mensagem_sefaz = models.TextField(blank=True, null=True)

    cnpj_emitente = models.CharField(max_length=14)
    natureza_operacao = models.CharField(max_length=100, default="Venda de mercadoria")
    
    # Novos campos para Modelo 55
    tipo_documento = models.IntegerField(default=1) # 1=Saída, 0=Entrada
    finalidade_emissao = models.IntegerField(default=1) # 1=Normal

    cnpj_destinatario = models.CharField(max_length=14, blank=True, null=True)
    cpf_destinatario = models.CharField(max_length=11, blank=True, null=True)
    nome_destinatario = models.CharField(max_length=255, blank=True, null=True)
    valor_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    caminho_xml = models.TextField(blank=True, null=True)
    caminho_danfe = models.TextField(blank=True, null=True)
    caminho_xml_cancelamento = models.TextField(blank=True, null=True)

    payload_enviado = models.JSONField(null=True, blank=True)
    resposta_focusnfe = models.JSONField(null=True, blank=True)

    justificativa_cancelamento = models.TextField(blank=True, null=True)
    cancelado_em = models.DateTimeField(null=True, blank=True)

    tentativas_consulta = models.PositiveIntegerField(default=0)
    ultima_consulta_em = models.DateTimeField(null=True, blank=True)

    venda = models.ForeignKey(Venda, on_delete=models.PROTECT, null=True, blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "NF-e"
        verbose_name_plural = "NF-es"
        indexes = [
            models.Index(fields=["status", "is_deleted"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["cnpj_emitente", "status"]),
        ]

    def __str__(self):
        return f"NF-e {self.numero or self.ref} [{self.status}]"

    @property
    def foi_autorizada(self) -> bool:
        return self.status == NFeStatus.AUTORIZADO

    @property
    def esta_processando(self) -> bool:
        return self.status in (NFeStatus.PENDENTE, NFeStatus.PROCESSANDO)

    @property
    def pode_cancelar(self) -> bool:
        """NF-e pode ser cancelada até 24h após emissão."""
        if self.status != NFeStatus.AUTORIZADO:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at >= timezone.now() - timedelta(hours=23, minutes=30)

class NFeRecebida(BaseModel):
    """
    Representa uma NF-e emitida por terceiros contra o CNPJ da empresa (MDe).
    Obtida via endpoint /nfes_recebidas da Focus NFe.
    """
    MANIF_CHOICES = [
        ('nulo', 'Não Manifestada'),
        ('ciencia', 'Ciência da Operação'),
        ('confirmacao', 'Confirmação da Operação'),
        ('desconhecimento', 'Desconhecimento da Operação'),
        ('nao_realizada', 'Operação não Realizada'),
    ]
    
    chave_nfe = models.CharField(max_length=50, unique=True, db_index=True)
    nome_emitente = models.CharField(max_length=255)
    documento_emitente = models.CharField(max_length=20)
    
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    data_emissao = models.DateTimeField()
    
    situacao = models.CharField(max_length=20) # autorizada, cancelada, denegada
    manifestacao_destinatario = models.CharField(
        max_length=20, 
        choices=MANIF_CHOICES, 
        default='nulo'
    )
    
    versao = models.IntegerField(help_text="Versão do documento na Focus NFe para controle de sincronização")
    xml_completo = models.TextField(blank=True, null=True)
    nfe_completa = models.BooleanField(default=False)
    
    # Vinculação com o módulo de compras após importação
    nota_compra = models.OneToOneField(
        'compras.NotaCompra', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='nfe_recebida'
    )

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = "NF-e Recebida"
        verbose_name_plural = "NF-es Recebidas"
        ordering = ['-data_emissao']
        indexes = [
            models.Index(fields=["chave_nfe"]),
            models.Index(fields=["documento_emitente"]),
        ]

    def __str__(self):
        return f"NF-e {self.chave_nfe[-8:]} - {self.nome_emitente}"
