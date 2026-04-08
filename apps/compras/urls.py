from rest_framework.routers import DefaultRouter
from .views import NotaCompraViewSet

router = DefaultRouter()
router.register(r'notas-compra', NotaCompraViewSet, basename='nota-compra')

urlpatterns = router.urls
