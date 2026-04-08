from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connection
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import timedelta

@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint para verificação de integridade do sistema (Health Check).
    Verifica se a conexão com o banco de dados está ativa.
    """
    try:
        connection.ensure_connection()
        return Response({
            "status": "ok", 
            "database": "connected",
            "message": "Sistema JR Sacolões está online."
        })
    except Exception as e:
        return Response({
            "status": "error", 
            "database": "disconnected",
            "error": str(e)
        }, status=503)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_stats(request):
    """
    Retorna estatísticas consolidadas para o dashboard.
    """
    from apps.vendas.models import Venda
    from apps.produtos.models import EstoqueLoja, Produto
    
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # 1. KPIs Financeiros
    vendas_hoje = Venda.objects.filter(status='FINALIZADA', created_at__date=today)
    faturamento_hoje = vendas_hoje.aggregate(total=Sum('total'))['total'] or 0
    total_vendas_hoje = vendas_hoje.count()
    
    vendas_mes = Venda.objects.filter(status='FINALIZADA', created_at__date__gte=start_of_month)
    faturamento_mes = vendas_mes.aggregate(total=Sum('total'))['total'] or 0
    
    # 2. Estoque e Rupturas
    # Itens com menos de 5 unidades/kg
    criticos = EstoqueLoja.objects.filter(quantidade__lte=5).select_related('produto')
    total_criticos = criticos.count()
    
    # 3. Gráfico de 7 dias
    grafico_vendas = []
    for i in range(6, -1, -1):
        dia = today - timedelta(days=i)
        valor_dia = Venda.objects.filter(status='FINALIZADA', created_at__date=dia).aggregate(total=Sum('total'))['total'] or 0
        grafico_vendas.append({
            "data": dia.strftime("%d/%m"),
            "total": float(valor_dia)
        })

    return Response({
        "faturamento_hoje": float(faturamento_hoje),
        "total_vendas_hoje": total_vendas_hoje,
        "faturamento_mes": float(faturamento_mes),
        "itens_criticos": total_criticos,
        "grafico_vendas": grafico_vendas,
        "produtos_ruptura": [
            {"id": c.produto.id, "nome": c.produto.nome, "qtd": float(c.quantidade)}
            for c in criticos[:5] # Apenas os 5 mais urgentes
        ]
    })
