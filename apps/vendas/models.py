from django.db import models
from django.contrib.auth.models import User
from apps.clientes.models import Cliente
from apps.produtos.models import Produto, EstoqueLoja
from apps.core.models import BaseModel, ActiveManager


class SessaoCaixa(BaseModel):
    STATUS_CHOICES = [('ABERTA', 'Aberta'), ('FECHADA', 'Fechada')]
    operador = models.ForeignKey(User, on_delete=models.PROTECT)
    fundo_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    data_abertura = models.DateTimeField(auto_now_add=True)
    data_fechamento = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ABERTA')
    observacoes = models.TextField(blank=True)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'vendas'

    def __str__(self):
        return f"Caixa {self.pk} - {self.operador.username} - {self.status}"


class Venda(BaseModel):
    STATUS_CHOICES = [
        ('EM_ABERTO', 'Em Aberto'),
        ('FINALIZADA', 'Finalizada'),
        ('CANCELADA', 'Cancelada'),
    ]
    sessao = models.ForeignKey(SessaoCaixa, on_delete=models.PROTECT)
    cliente = models.ForeignKey(Cliente, null=True, blank=True, on_delete=models.SET_NULL)
    data = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='EM_ABERTO')
    observacoes = models.TextField(blank=True)
    
    # Novos campos fiscais
    nf_emitida = models.BooleanField(default=False)
    nf_id_fiscal = models.UUIDField(null=True, blank=True, help_text="ID interno do Bridge")
    nf_chave = models.CharField(max_length=44, blank=True, null=True)
    nf_numero = models.CharField(max_length=20, blank=True, null=True)
    nf_serie = models.CharField(max_length=5, blank=True, null=True)
    nf_protocolo = models.CharField(max_length=50, blank=True, null=True)
    nf_qr_code = models.TextField(blank=True, null=True)
    nf_url_pdf = models.URLField(max_length=500, blank=True, null=True)
    nf_status = models.CharField(max_length=20, blank=True, null=True) # PENDENTE, AUTORIZADA, REJEITADA
    nf_mensagem = models.TextField(blank=True, null=True, help_text="Mensagem de retorno da SEFAZ")

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'vendas'

    def __str__(self):
        return f"Venda #{self.pk} - R$ {self.total}"


class VendaItem(BaseModel):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'vendas'

    def save(self, *args, **kwargs):
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.produto.nome} x {self.quantidade}"


class VendaPagamento(BaseModel):
    FORMA_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('CARTAO_DEBITO', 'Cartão Débito'),
        ('CARTAO_CREDITO', 'Cartão Crédito'),
        ('PIX', 'Pix'),
        ('FIADO', 'Fiado'),
    ]
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='pagamentos')
    forma = models.CharField(max_length=20, choices=FORMA_CHOICES)
    valor = models.DecimalField(max_digits=12, decimal_places=2)

    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'vendas'

    def __str__(self):
        return f"{self.forma}: R$ {self.valor}"


class OperacaoCaixa(BaseModel):
    TIPO_CHOICES = [('SANGRIA', 'Sangria'), ('SUPRIMENTO', 'Suprimento')]
    
    sessao = models.ForeignKey(SessaoCaixa, on_delete=models.CASCADE, related_name='operacoes')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(max_length=255, blank=True)
    
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'vendas'

    def __str__(self):
        return f"{self.tipo} - R$ {self.valor}"
