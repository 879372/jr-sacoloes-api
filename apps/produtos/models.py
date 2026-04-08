from django.db import models
from apps.core.models import BaseModel, ActiveManager

class Produto(BaseModel):
    codigo_legado = models.IntegerField(unique=True, null=True, blank=True, help_text="Código da Mercadoria no sistema legado")
    nome = models.CharField(max_length=255)
    codigo_barras = models.CharField(max_length=100, blank=True, null=True)
    
    # Preços
    preco_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Detalhes
    unidade_medida = models.CharField(max_length=10, default='UN')
    grupo = models.CharField(max_length=100, blank=True, null=True)
    subgrupo = models.CharField(max_length=100, blank=True, null=True)
    ativo = models.BooleanField(default=True)
    
    # Fiscal
    ncm = models.CharField(max_length=10, blank=True, null=True)
    cest = models.CharField(max_length=10, blank=True, null=True)
    origem = models.CharField(max_length=2, default='0', help_text="Origem da mercadoria (0 - Nacional, etc)")
    cfop_padrao = models.CharField(max_length=5, blank=True, null=True)
    
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'produtos'

    def __str__(self):
        return f"{self.codigo_legado} - {self.nome}"

class EstoqueLoja(BaseModel):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='estoques')
    loja = models.CharField(max_length=100)
    quantidade = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        unique_together = ('produto', 'loja')
        app_label = 'produtos'

    def __str__(self):
        return f"{self.produto.nome} - {self.loja}: {self.quantidade}"

class MovimentacaoEstoque(BaseModel):
    TIPO_CHOICES = [('ENTRADA', 'Entrada'), ('SAIDA', 'Saída')]
    MOTIVO_CHOICES = [
        ('VENDA', 'Venda'),
        ('COMPRA', 'Compra'),
        ('AJUSTE', 'Ajuste Manual'),
        ('DEVOLUCAO', 'Devolução'),
        ('OUTRO', 'Outro'),
    ]
    
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
    quantidade = models.DecimalField(max_digits=15, decimal_places=3)
    saldo_anterior = models.DecimalField(max_digits=15, decimal_places=3)
    saldo_atual = models.DecimalField(max_digits=15, decimal_places=3, default=0)
    observacoes = models.TextField(blank=True)
    
    objects = ActiveManager()
    all_objects = models.Manager()

    class Meta:
        app_label = 'produtos'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.produto.nome} ({self.tipo}): {self.quantidade}"
