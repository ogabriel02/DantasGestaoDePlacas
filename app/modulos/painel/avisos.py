"""Rotina periodica do ator Tempo (UC12).

Pedido parado = situacao diferente de FINALIZADO/CANCELADO e sem atualizacao ha mais de N dias
(pedido.atualizado_em e mantido pelo trigger bu_pedido_atualizado). N vem de DIAS_PEDIDO_PARADO
no .env (padrao 3).

O banco nao tem procedure para pedido parado; o aviso e gravado com INSERT em aviso, coluna
liberada para a aplicacao pelo 04_permissoes_aplicacao.sql (o 02_dados_exemplo.sql faz igual).
Avisos de estoque continuam pela procedure sp_gerar_avisos_estoque.

Uso agendado:  flask --app run painel gerar-avisos
"""
import os

from flask import current_app

from app import db

DIAS_PADRAO = 3

_SITUACAO = """CASE p.situacao WHEN 'CRIADO' THEN 'Criado'
                 WHEN 'AGUARDANDO_PAGAMENTO' THEN 'Aguardando pagamento'
                 WHEN 'EM_PRODUCAO' THEN 'Em produção' ELSE p.situacao END"""

_INSERIR_PARADOS = f"""
INSERT INTO public.aviso (pedido_numero, tipo, mensagem)
SELECT p.numero, 'PEDIDO_PARADO',
       left(concat('Pedido ', p.numero, ' parado há ',
                   floor(extract(epoch FROM (LOCALTIMESTAMP - p.atualizado_em)) / 86400)::int,
                   ' dia(s) em "', {_SITUACAO}, '" (', c.nome, ')'), 255)
FROM public.pedido p JOIN public.cliente c ON c.id = p.cliente_id
WHERE p.situacao NOT IN ('FINALIZADO', 'CANCELADO')
  AND p.atualizado_em < LOCALTIMESTAMP - make_interval(days => %s)
  AND NOT EXISTS (SELECT 1 FROM public.aviso a
                  WHERE a.pedido_numero = p.numero AND a.tipo = 'PEDIDO_PARADO' AND NOT a.lido)
"""


def dias_parado():
    """Dias sem atualizacao para considerar um pedido parado (config > .env > padrao)."""
    valor = current_app.config.get("DIAS_PEDIDO_PARADO", os.environ.get("DIAS_PEDIDO_PARADO", DIAS_PADRAO))
    try:
        dias = int(valor)
    except (TypeError, ValueError):
        return DIAS_PADRAO
    return dias if 1 <= dias <= 365 else DIAS_PADRAO


def gerar(dias=None):
    """Gera avisos de pedidos parados e de estoque numa unica transacao.

    Retorna {"pedidos": n, "estoque": n} com a quantidade de avisos novos.
    """
    dias = dias_parado() if dias is None else dias
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(_INSERIR_PARADOS, (dias,))
            pedidos = cur.rowcount
            cur.execute("SELECT count(*) AS n FROM public.aviso WHERE item_estoque_id IS NOT NULL")
            antes = cur.fetchone()["n"]
            cur.execute("CALL public.sp_gerar_avisos_estoque()")
            cur.execute("SELECT count(*) AS n FROM public.aviso WHERE item_estoque_id IS NOT NULL")
            estoque = cur.fetchone()["n"] - antes
        conn.commit()
        return {"pedidos": pedidos, "estoque": estoque}
    except Exception:
        conn.rollback()
        raise
