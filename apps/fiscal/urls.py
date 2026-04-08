from rest_framework.routers import DefaultRouter
from django.urls import path
from .views.old_views import NotaFiscalEmitidaViewSet
from .views.nfce_views import NFCeViewSet
from .views.nfe_views import NFeViewSet
from .views.nfe_recebida_views import NFeRecebidaViewSet
from .views.webhooks import FocusNFeWebhookView

router = DefaultRouter()
router.register(r'notas-fiscais', NotaFiscalEmitidaViewSet, basename='nota-fiscal')
router.register(r'nfce', NFCeViewSet, basename='nfce')
router.register(r'nfe', NFeViewSet, basename='nfe')
router.register(r'recebidas', NFeRecebidaViewSet, basename='nfe-recebida')

urlpatterns = [
    path('webhooks/focusnfe/', FocusNFeWebhookView.as_view(), name='focusnfe-webhook'),
] + router.urls
