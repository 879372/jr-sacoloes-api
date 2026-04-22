from django.db import models, transaction
from django.db.models import Q
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
import requests
from decouple import config
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import SessaoCaixa, Venda, VendaItem, VendaPagamento, OperacaoCaixa
from .serializers import (
    SessaoCaixaSerializer, 
    VendaSerializer, 
    VendaReadSerializer,
    VendaItemSerializer, 
    VendaPagamentoSerializer,
    OperacaoCaixaSerializer,
    VendaFinalizarSerializer
)


@extend_schema(tags=['Caixa'])
class SessaoCaixaViewSet(viewsets.ModelViewSet):
    queryset = SessaoCaixa.objects.all().select_related('operador')
    serializer_class = SessaoCaixaSerializer

    def perform_create(self, serializer):
        serializer.save(operador=self.request.user)

    @action(detail=False, methods=['get'], url_path='ativa')
    def sessao_ativa(self, request):
        """Retorna a sessão de caixa aberta do usuário atual, se houver."""
        sessao = SessaoCaixa.objects.filter(operador=request.user, status='ABERTA').last()
        if sessao:
            return Response(SessaoCaixaSerializer(sessao).data)
        return Response(None)

    @action(detail=True, methods=['post'], url_path='fechar')
    def fechar(self, request, pk=None):
        """Fecha a sessão de caixa e retorna o resumo financeiro."""
        from django.utils import timezone
        sessao = self.get_object()
        
        if sessao.status == 'FECHADA':
            return Response({'erro': 'Este caixa já está fechado.'}, status=400)
            
        # Impede fechar se houver vendas em aberto
        vendas_abertas = Venda.objects.filter(sessao=sessao, status='EM_ABERTO').exists()
        if vendas_abertas:
            return Response({'erro': 'Não é possível fechar o caixa com vendas em aberto. Finalize ou cancele as vendas pendentes.'}, status=400)
            
        # Calcula resumo
        vendas = Venda.objects.filter(sessao=sessao, status='FINALIZADA')
        pagamentos = VendaPagamento.objects.filter(venda__in=vendas)
        
        resumo = {
            'total_vendas': sum(v.total for v in vendas),
            'quantidade_vendas': vendas.count(),
            'por_forma': {}
        }
        
        for forma, label in VendaPagamento.FORMA_CHOICES:
            total_forma = sum(p.valor for p in pagamentos if p.forma == forma)
            resumo['por_forma'][forma] = total_forma

        sessao.status = 'FECHADA'
        sessao.data_fechamento = timezone.now()
        sessao.save()
        
        return Response({
            'sessao': SessaoCaixaSerializer(sessao).data,
            'resumo': resumo
        })

    @action(detail=True, methods=['post'], url_path='sangria')
    def sangria(self, request, pk=None):
        sessao = self.get_object()
        if sessao.status == 'FECHADA':
            return Response({'erro': 'Caixa fechado.'}, status=400)
        
        valor = request.data.get('valor')
        motivo = request.data.get('motivo', '')
        
        if not valor or float(valor) <= 0:
            return Response({'erro': 'Valor inválido.'}, status=400)
            
        op = OperacaoCaixa.objects.create(
            sessao=sessao, tipo='SANGRIA', valor=valor, motivo=motivo
        )
        return Response(OperacaoCaixaSerializer(op).data, status=201)

    @action(detail=True, methods=['post'], url_path='suprimento')
    def suprimento(self, request, pk=None):
        sessao = self.get_object()
        if sessao.status == 'FECHADA':
            return Response({'erro': 'Caixa fechado.'}, status=400)
            
        valor = request.data.get('valor')
        motivo = request.data.get('motivo', '')
        
        if not valor or float(valor) <= 0:
            return Response({'erro': 'Valor inválido.'}, status=400)
            
        op = OperacaoCaixa.objects.create(
            sessao=sessao, tipo='SUPRIMENTO', valor=valor, motivo=motivo
        )
        return Response(OperacaoCaixaSerializer(op).data, status=201)


@extend_schema(tags=['Vendas'])
class VendaViewSet(viewsets.ModelViewSet):
    queryset = Venda.objects.all().select_related(
        'cliente', 'sessao', 'sessao__operador'
    ).prefetch_related(
        'itens__produto', 'pagamentos'
    )
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['data', 'total', 'status']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve', 'finalizar', 'cancelar']:
            return VendaReadSerializer
        return VendaSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        sessao = self.request.query_params.get('sessao')
        status = self.request.query_params.get('status')
        data_inicio = self.request.query_params.get('data_inicio')
        data_fim = self.request.query_params.get('data_fim')

        nf_emitida = self.request.query_params.get('nf_emitida')
        nf_tipo = self.request.query_params.get('nf_tipo')

        if sessao:
            queryset = queryset.filter(sessao_id=sessao)
        if status:
            queryset = queryset.filter(status=status)
        if data_inicio:
            queryset = queryset.filter(data__date__gte=data_inicio)
        if data_fim:
            queryset = queryset.filter(data__date__lte=data_fim)
        
        if nf_emitida:
            queryset = queryset.filter(nf_emitida=nf_emitida.lower() == 'true')
        if nf_tipo:
            queryset = queryset.filter(nf_tipo=nf_tipo.lower())
        
        return queryset.order_by('-data')

    @extend_schema(
        summary="Finalizar uma venda",
        description="Fecha a venda, registra os pagamentos, baixa o estoque e opcionalmente emite nota fiscal.",
        request=VendaFinalizarSerializer,
        responses={200: VendaReadSerializer}
    )
    @action(detail=True, methods=['post'], url_path='finalizar')
    def finalizar(self, request, pk=None):
        # ... (Logica de finalização mantida igual, apenas retornando o serializer correto)
        venda = self.get_object()

        if venda.status != 'EM_ABERTO':
            return Response({'erro': 'Apenas vendas em aberto podem ser finalizadas.'}, status=400)

        pagamentos_data = request.data.get('pagamentos', [])
        cliente_id = request.data.get('cliente')
        
        if not pagamentos_data:
            return Response({'erro': 'Informe ao menos uma forma de pagamento.'}, status=400)

        from decimal import Decimal
        total_pago = sum(Decimal(str(p.get('valor', 0))) for p in pagamentos_data)
        
        if total_pago < venda.total - Decimal('0.05'):
             return Response({
                 'erro': f'O total dos pagamentos (R${total_pago:.2f}) não atinge o total da venda (R${venda.total:.2f}).'
             }, status=400)

        troco = total_pago - venda.total
        if troco > Decimal('0.05'):
            pagamento_dinheiro = next((p for p in pagamentos_data if str(p.get('forma', '')).strip().upper() == 'DINHEIRO'), None)
            if not pagamento_dinheiro:
                formas_enviadas = [p.get('forma') for p in pagamentos_data]
                return Response({
                    'erro': f'Pagamento maior que o total suportado apenas para DINHEIRO (Troco). Formas enviadas: {formas_enviadas}'
                }, status=400)
            
            valor_em_dinheiro = Decimal(str(pagamento_dinheiro.get('valor', 0)))
            if troco > valor_em_dinheiro + Decimal('0.05'):
                 return Response({
                    'erro': 'O troco é maior do que o valor pago em dinheiro, o que é inválido.'
                 }, status=400)
            
            # Abate o troco no pagamento em dinheiro para que o banco de dados armazene apenas o valor real recebido
            pagamento_dinheiro['valor'] = float(valor_em_dinheiro - troco)
        try:
            with transaction.atomic():
                itens = venda.itens.select_related('produto').all()
                if not itens:
                    raise ValueError('O carrinho está vazio.')

                from apps.produtos.services import registrar_movimentacao
                
                for item in itens:
                    registrar_movimentacao(
                        produto_id=item.produto_id,
                        quantidade=item.quantidade,
                        tipo='SAIDA',
                        motivo='VENDA',
                        loja=venda.sessao.operador.username or 'Matriz',
                        observacoes=f'Venda #{venda.id}'
                    )

                for p in pagamentos_data:
                    VendaPagamento.objects.create(venda=venda, forma=p['forma'], valor=p['valor'])
                    
                    # Se for FIADO, gera Conta a Receber
                    if str(p['forma']).strip().upper() == 'FIADO':
                        from apps.financeiro.models import ContaReceber
                        from django.utils import timezone
                        from datetime import timedelta
                        
                        nome_cliente = "Consumidor Final"
                        if cliente_id:
                            from apps.clientes.models import Cliente
                            try:
                                cli = Cliente.objects.get(id=cliente_id)
                                nome_cliente = cli.nome
                            except:
                                pass
                        elif venda.cliente:
                            nome_cliente = venda.cliente.nome

                        ContaReceber.objects.create(
                            descricao=f"Venda FIADO #{venda.id}",
                            cliente_nome=nome_cliente,
                            valor=p['valor'],
                            vencimento=timezone.now().date() + timedelta(days=30), # Padrão 30 dias
                            status='PENDENTE',
                            observacoes=f'Originada da Venda #{venda.id} no PDV.'
                        )

                venda.status = 'FINALIZADA'
                venda.nf_emitida = request.data.get('emitir_fiscal', False)
                if cliente_id:
                    venda.cliente_id = cliente_id
                venda.save()

                # Se solicitou emissão fiscal, tenta emitir AGORA dentro da transação
                if venda.nf_emitida:
                    self._executar_emissao_fiscal_venda(venda)

        except Exception as e:
            # Captura erros amigáveis (como os da SEFAZ) e retorna 400
            msg = str(e)
            if "Erro na API Fiscal" in msg or "SEFAZ" in msg:
                return Response({'erro': msg}, status=400)
            return Response({'erro': f'Erro ao finalizar: {msg}'}, status=400)

        return Response(VendaReadSerializer(venda).data)

    def _executar_emissao_fiscal_venda(self, venda, tipo=None):
        """
        Método interno para realizar a chamada ao Gateway Fiscal.
        Lança exceção em caso de erro para permitir rollback da transação de finalização.
        """
        modelo_doc = tipo or venda.nf_tipo or 'nfce'
        
        # Monta Payload para o Gateway Fiscal
        itens_fiscal = []
        for item in venda.itens.select_related('produto').all():
            itens_fiscal.append({
                "codigo": item.produto.codigo_barras or str(item.produto.id),
                "descricao": (item.produto.nome or "PRODUTO")[:200],
                "ncm": (item.produto.ncm or "00000000").replace('.', '').strip(),
                "cfop": item.produto.cfop_padrao or ("5102" if modelo_doc == 'nfce' else "5102"),      
                "unidade": (item.produto.unidade_medida or "UN")[:6],
                "quantidade": float(item.quantidade),
                "valor_unitario": float(item.preco_unitario),
                "valor_total": float(item.subtotal),
                "cst_icms": "00"
            })

        pagamentos = []
        for p in venda.pagamentos.all():
            forma_map = {
                'DINHEIRO': '01',
                'CARTAO_CREDITO': '03',
                'CARTAO_DEBITO': '04',
                'PIX': '17',
                'FIADO': '99'
            }
            pagamentos.append({
                "forma": forma_map.get(str(p.forma).upper(), '99'),
                "valor": float(p.valor)
            })

        payload = {
            "cnpj_emitente": config('EMPRESA_CNPJ', default='00000000000000'),
            "itens": itens_fiscal,
            "total": float(venda.total),
            "pagamento": pagamentos,
            "ambiente": "homologacao", # TODO: Mudar para 'producao' em prod
            "presenca": "1" # Presencial
        }

        if venda.cliente:
            payload["destinatario"] = {
                "cpf": venda.cliente.cpf_cnpj.replace('.', '').replace('-', '').replace('/', '') if venda.cliente.cpf_cnpj else None,
                "nome": venda.cliente.nome
            }

        # Seleciona endpoint conforme o tipo
        endpoint = "nfe" if modelo_doc == 'nfe' else "nfce"
        fiscal_url = f"{config('FISCAL_API_URL').rstrip('/')}/{endpoint}/emitir/"
        fiscal_key = config('FISCAL_API_KEY')

        try:
            resp = requests.post(
                fiscal_url, 
                json=payload, 
                headers={'X-Api-Key': fiscal_key},
                timeout=30
            )
            
            if resp.status_code in [200, 201]:
                data = resp.json()
                venda.nf_tipo = modelo_doc
                venda.nf_id_fiscal = data.get('id')
                venda.nf_chave = data.get('chave_acesso')
                venda.nf_numero = data.get('numero')
                venda.nf_serie = data.get('serie')
                venda.nf_protocolo = data.get('protocolo')
                venda.nf_qr_code = data.get('qr_code')
                venda.nf_url_pdf = data.get('url_consulta') or data.get('caminho_danfe')
                venda.nf_status = 'AUTORIZADA'
                venda.nf_mensagem = data.get('mensagem_sefaz')
                venda.save()
                return data
            else:
                try:
                    error_data = resp.json()
                    msg = error_data.get('detail') or error_data.get('mensagem') or 'Erro desconhecido'
                except:
                    msg = f"HTTP {resp.status_code}"
                
                venda.nf_status = 'ERRO'
                venda.save()
                raise ValueError(f"Erro na API Fiscal: {msg}")

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Falha ao conectar com o gateway fiscal: {str(e)}")

    @action(detail=True, methods=['post'], url_path='cancelar')
    def cancelar(self, request, pk=None):
        # ... (Mantido igual)
        venda = self.get_object()
        if venda.status == 'CANCELADA':
            return Response({'erro': 'Esta venda já está cancelada.'}, status=400)
            
        if venda.nf_emitida and venda.nf_status == 'AUTORIZADA' and venda.nf_chave:
            endpoint = "nfe" if venda.nf_tipo == 'nfe' else "nfce"
            fiscal_url = f"{config('FISCAL_API_URL').rstrip('/')}/{endpoint}/{venda.nf_chave}/cancelar/"
            fiscal_key = config('FISCAL_API_KEY')
            justificativa = request.data.get('justificativa', 'Venda cancelada por desistencia do cliente ou erro de digitacao')
            
            if len(justificativa) < 15:
                return Response({'erro': 'A justificativa de cancelamento fiscal deve ter pelo menos 15 caracteres.'}, status=400)

            try:
                resp = requests.post(
                    fiscal_url, 
                    json={"justificativa": justificativa}, 
                    headers={'X-Api-Key': fiscal_key},
                    timeout=30
                )
                if resp.status_code == 200:
                    venda.nf_status = 'CANCELADA'
                else:
                    try:
                        err_msg = resp.json().get('mensagem') or resp.json().get('detail')
                    except:
                        err_msg = f"Erro SEFAZ (Status {resp.status_code})"
                    return Response({'erro': f'Erro ao cancelar nota na SEFAZ: {err_msg}'}, status=400)
            except Exception as e:
                return Response({'erro': f'Falha ao conectar com gateway fiscal para cancelamento: {str(e)}'}, status=500)

        try:
            with transaction.atomic():
                if venda.status == 'FINALIZADA':
                    from apps.produtos.services import registrar_movimentacao
                    for item in venda.itens.all():
                        registrar_movimentacao(
                            produto_id=item.produto_id,
                            quantidade=item.quantidade,
                            tipo='ENTRADA',
                            motivo='DEVOLUCAO',
                            loja=venda.sessao.operador.username or 'Matriz',
                            observacoes=f'Estorno Venda #{venda.id} (Cancelamento)'
                        )

                venda.status = 'CANCELADA'
                venda.save()
        except Exception as e:
            return Response({'erro': str(e)}, status=400)

        return Response(VendaReadSerializer(venda).data)

    @action(detail=True, methods=['post'], url_path='emitir-nfce')
    def emitir_nfce(self, request, pk=None):
        venda = self.get_object()
        tipo = request.data.get('tipo') # Permite forçar 'nfe' ou 'nfce'
        
        if venda.status != 'FINALIZADA':
            return Response({'erro': 'Apenas vendas FINALIZADAS podem emitir nota fiscal.'}, status=400)
        
        try:
            data = self._executar_emissao_fiscal_venda(venda, tipo=tipo)
            return Response(data)
        except ValueError as e:
            return Response({'erro': str(e)}, status=400)

class VendaItemViewSet(viewsets.ModelViewSet):
    queryset = VendaItem.objects.all().select_related('produto')
    serializer_class = VendaItemSerializer


class VendaPagamentoViewSet(viewsets.ModelViewSet):
    queryset = VendaPagamento.objects.all()
    serializer_class = VendaPagamentoSerializer

class OperacaoCaixaViewSet(viewsets.ModelViewSet):
    queryset = OperacaoCaixa.objects.all()
    serializer_class = OperacaoCaixaSerializer
