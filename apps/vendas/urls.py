from rest_framework.routers import DefaultRouter
from .views import (
    SessaoCaixaViewSet, VendaViewSet, VendaItemViewSet, 
    VendaPagamentoViewSet, OperacaoCaixaViewSet
)

router = DefaultRouter()
router.register(r'sessoes-caixa', SessaoCaixaViewSet, basename='sessao-caixa')
router.register(r'vendas', VendaViewSet, basename='venda')
router.register(r'venda-itens', VendaItemViewSet, basename='venda-item')
router.register(r'venda-pagamentos', VendaPagamentoViewSet, basename='venda-pagamento')
router.register(r'operacoes-caixa', OperacaoCaixaViewSet, basename='operacao-caixa')

urlpatterns = router.urls
