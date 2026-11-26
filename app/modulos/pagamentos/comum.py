"""Rotulos e traducao de mensagens do banco usados pelos modulos da parte 3 (Jonathan).

As regras de negocio ficam nas procedures. Aqui apenas deixamos as mensagens
delas (que vem sem acento e em tom tecnico) mais claras para o usuario.
Mensagem desconhecida e exibida exatamente como o banco a enviou.
"""
from decimal import Decimal

from app import db

SITUACOES = {
    "CRIADO": "Criado",
    "AGUARDANDO_PAGAMENTO": "Aguardando pagamento",
    "EM_PRODUCAO": "Em produção",
    "FINALIZADO": "Finalizado",
    "CANCELADO": "Cancelado",
}
SELO_SITUACAO = {
    "CRIADO": "neutro",
    "AGUARDANDO_PAGAMENTO": "alerta",
    "EM_PRODUCAO": "info",
    "FINALIZADO": "ok",
    "CANCELADO": "erro",
}
AUTORIZACOES = {
    None: "Não iniciada",
    "NAO_SOLICITADA": "Não solicitada",
    "PENDENTE": "Aguardando autorização",
    "LIBERADA": "Liberada",
    "NEGADA": "Negada",
}
ESTADOS_ESTOQUE = {"DISPONIVEL": "Disponível", "NIVEL_MINIMO": "No nível mínimo", "ESGOTADO": "Esgotado"}
SELO_ESTOQUE = {"DISPONIVEL": "ok", "NIVEL_MINIMO": "alerta", "ESGOTADO": "erro"}
MOVIMENTACOES = {
    "ENTRADA": "Entrada",
    "SAIDA": "Saída (pedido finalizado)",
    "AJUSTE_ENTRADA": "Ajuste para mais",
    "AJUSTE_SAIDA": "Ajuste para menos",
}
PAGAMENTOS = {"PENDENTE": "Pendente", "CONFIRMADO": "Confirmado", "CANCELADO": "Cancelado"}
SELO_PAGAMENTO = {"PENDENTE": "alerta", "CONFIRMADO": "ok", "CANCELADO": "erro"}

# Mensagens das procedures/triggers (01_criar_banco.sql) -> texto para o usuario.
_MENSAGENS = {
    "Cobranca exige pedido CRIADO": "A cobrança só pode ser gerada para pedidos na situação \"Criado\".",
    "Confirmacao exige AGUARDANDO_PAGAMENTO": "O pagamento só pode ser confirmado em pedidos \"Aguardando pagamento\".",
    "Pagamento pendente inexistente": "Não existe cobrança pendente para este pedido.",
    "Finalizacao exige EM_PRODUCAO": "Só é possível finalizar pedidos \"Em produção\" (com pagamento confirmado).",
    "Finalizacao exige autorizacao LIBERADA": "O pedido só pode ser finalizado com a autorização externa liberada.",
    "Finalizacao exige de uma a duas placas": "O pedido precisa ter uma ou duas placas para ser finalizado.",
    "Item inexistente ou estoque insuficiente": "Estoque insuficiente para concluir a operação (ou modelo de placa inexistente).",
    "Quantidade da movimentacao deve ser positiva": "A quantidade deve ser maior que zero.",
    "Cadastre item com saldo zero e registre ENTRADA": "Cadastre o modelo com saldo zero e registre uma entrada em seguida.",
}
# Restricoes das minhas tabelas que o db.traduzir_erro ainda nao conhece.
_RESTRICOES = {
    "uk_pagamento_pedido": "Este pedido já possui cobrança.",
    "ck_pagamento_valor": "O valor da cobrança deve ser maior que zero.",
    "ck_pagamento_forma": "Forma de pagamento inválida.",
    "ck_mov_tipo": "Tipo de movimentação inválido.",
    "ck_mov_quantidade": "A quantidade deve ser maior que zero.",
    "fk_mov_item": "O modelo de placa informado não existe.",
    "uk_item_modelo": "Já existe um modelo de placa com este nome.",
    "ck_item_minimo": "O nível mínimo não pode ser negativo.",
    "ck_aviso_lido": "Situação de leitura do aviso inválida.",
}


def mensagem_erro(exc):
    """Mensagem clara para um erro do banco, ou None se o erro nao for do banco."""
    restricao = getattr(getattr(exc, "diag", None), "constraint_name", None)
    if restricao in _RESTRICOES:
        return _RESTRICOES[restricao]
    erro = db.traduzir_erro(exc)
    if erro is None:
        return None
    return _MENSAGENS.get(erro.mensagem.strip(), erro.mensagem)


def formatar_moeda(valor):
    if valor is None:
        return ""
    texto = f"{Decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")
