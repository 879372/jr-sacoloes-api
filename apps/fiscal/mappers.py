from decimal import Decimal

def venda_to_focus_nfe(venda):
    """
    Converte um objeto Venda do Django para o formato JSON esperado pela Focus NFe.
    Referência: https://focusnfe.com.br/doc/#nfce_emitir
    """
    items = []
    for idx, item in enumerate(venda.itens.all(), 1):
        items.append({
            "numero_item": str(idx),
            "codigo_produto": str(item.produto.codigo_legado or item.produto.id),
            "descricao": item.produto.nome,
            "unidade_comercial": item.produto.unidade_medida or "UN",
            "quantidade_comercial": str(item.quantidade),
            "valor_unitario_comercial": str(item.preco_unitario),
            "valor_bruto": str(item.subtotal),
            "codigo_ncm": item.produto.ncm or "00000000",
            "codigo_cest": item.produto.cest or "",
            "cfop": item.produto.cfop_padrao or "5102",
            "icms_situacao_tributaria": "102",  # Simples Nacional - Tributação sem permissão de crédito
            "icms_origem": item.produto.origem or "0",
        })

    pagamentos = []
    # Mapeamento de formas do ERP para Focus NFe
    # 01-Dinheiro, 02-Cheque, 03-Cartão de Crédito, 04-Cartão de Débito, 15-Boleto Bancário, 17-PIX
    mapa_pagto = {
        'DINHEIRO': '01',
        'CARTAO_CREDITO': '03',
        'CARTAO_DEBITO': '04',
        'PIX': '17',
        'FIADO': '99' # Outros
    }

    for p in venda.pagamentos.all():
        pagamentos.append({
            "forma_pagamento": mapa_pagto.get(p.forma, '99'),
            "valor_pagamento": str(p.valor)
        })

    payload = {
        "data_emissao": venda.created_at.isoformat(),
        "presenca_comprador": "1", # Operação presencial
        "modalidade_frete": "9",    # Sem frete
        "local_destino": "1",       # Operação interna
        "consumidor_final": "1",    # 1 para consumidor final
        "finalidade_emissao": "1",  # 1 para NF-e normal
        "items": items,
        "formas_pagamento": pagamentos,
        "valor_total": str(venda.total)
    }

    # Se houver cliente com CPF
    if venda.cliente and venda.cliente.cpf_cnpj:
        payload["cpf_destinatario"] = "".join(filter(str.isdigit, venda.cliente.cpf_cnpj))
        payload["nome_destinatario"] = venda.cliente.nome

    return payload


def venda_to_focus_nfe_modelo_55(venda, natureza_operacao="Venda de mercadoria"):
    """
    Converte uma Venda para NF-e (Modelo 55).
    Requer dados completos do destinatário.
    """
    # Reutiliza a lógica base de itens e pagamentos
    payload = venda_to_focus_nfe(venda)
    
    # Ajustes específicos para Modelo 55
    payload["natureza_operacao"] = natureza_operacao
    payload["tipo_documento"] = 1 # 1=Saída
    payload["finalidade_emissao"] = 1 # 1=Normal
    payload["local_destino"] = "1" # 1=Interna
    
    # Itens na NF-e Modelo 55 podem exigir PIS/COFINS explícitos dependendo do regime
    for item in payload["items"]:
        item["pis_situacao_tributaria"] = "07" # Isento
        item["cofins_situacao_tributaria"] = "07" # Isento
    
    if venda.cliente:
        cliente = venda.cliente
        # Endereço é obrigatório na NF-e
        payload["logradouro_destinatario"] = cliente.endereco or "Nao Informado"
        payload["numero_destinatario"] = "S/N" 
        payload["bairro_destinatario"] = cliente.bairro or "Nao Informado"
        payload["municipio_destinatario"] = cliente.cidade or "Nao Informado"
        payload["uf_destinatario"] = cliente.uf or "SP"
        payload["cep_destinatario"] = "".join(filter(str.isdigit, cliente.cep or "00000000"))
        payload["telefone_destinatario"] = "".join(filter(str.isdigit, cliente.telefone or ""))
        
        if cliente.pessoa == 'J':
            payload["cnpj_destinatario"] = "".join(filter(str.isdigit, cliente.cpf_cnpj or ""))
            if cliente.inscricao_estadual:
                payload["inscricao_estadual_destinatario"] = cliente.inscricao_estadual
                payload["indicador_inscricao_estadual_destinatario"] = "1"
            else:
                payload["indicador_inscricao_estadual_destinatario"] = "9"
        else:
            payload["cpf_destinatario"] = "".join(filter(str.isdigit, cliente.cpf_cnpj or ""))
            payload["indicador_inscricao_estadual_destinatario"] = "9"
    else:
        # Nota sem cliente (Venda balcão) - NF-e costuma exigir destinatário
        # mas permitimos o payload base de consumidor final se for o caso
        payload["consumidor_final"] = "1"
        payload["indicador_inscricao_estadual_destinatario"] = "9"

    return payload
