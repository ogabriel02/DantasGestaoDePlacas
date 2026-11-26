"""Tabela de precos da cobranca (definida pela equipe).

O preco depende apenas da quantidade de placas do pedido, nao do modelo:
  - 1 placa (individual: moto, so traseira ou so dianteira) = R$ 180,00
  - 2 placas (par: dianteira + traseira)                    = R$ 250,00
O banco garante no maximo duas placas por pedido, uma por posicao (uk_placa_pedido_posicao).
"""
from decimal import Decimal

TABELA = {
    1: ("Placa individual", Decimal("180.00")),
    2: ("Par de placas", Decimal("250.00")),
}


def calcular(placas):
    """Retorna (descricao, valor) para as placas do pedido, ou (None, None) se nao houver preco."""
    return TABELA.get(len(placas), (None, None))
