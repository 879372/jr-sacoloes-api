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
    
    # 2. Compras do Mês (Entradas via NF)
    from apps.compras.models import NotaCompra
    compras_mes = NotaCompra.objects.filter(
        status='RECEBIDA', 
        data_entrada__gte=start_of_month
    ).aggregate(total=Sum('valor_total'))['total'] or 0
    
    # 3. Lucro por Categoria (Top 5)
    from apps.vendas.models import VendaItem
    from django.db.models import F
    
    lucro_categorias = VendaItem.objects.filter(
        venda__status='FINALIZADA',
        venda__created_at__date__gte=start_of_month
    ).values('produto__grupo').annotate(
        lucro=Sum((F('preco_unitario') - F('produto__preco_compra')) * F('quantidade'))
    ).order_by('-lucro')

    lucro_ranking = [
        {
            "name": item['produto__grupo'] or "Geral", 
            "total": float(item['lucro'] or 0)
        } 
        for item in lucro_categorias
    ]

    # 4. Gráfico de 7 dias
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
        "compras_mes": float(compras_mes),
        "grafico_vendas": grafico_vendas,
        "lucro_por_categoria": lucro_ranking
    })
