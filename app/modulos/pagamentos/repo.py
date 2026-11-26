"""Consultas e procedures de pagamento (UC06) e finalizacao (UC07).

Gravacoes somente por procedure: sp_gerar_cobranca, sp_confirmar_pagamento,
sp_finalizar_pedido e sp_gerar_avisos_estoque. Nenhum INSERT/UPDATE direto.
"""
from app import db, util

FORMA_PIX = "PIX"

_BASE = """FROM public.pedido p
           JOIN public.cliente c ON c.id = p.cliente_id
           LEFT JOIN public.pagamento pg ON pg.pedido_numero = p.numero"""


def _filtro(filtros):
    condicoes, params = [], []
    if filtros.get("situacao"):
        condicoes.append("p.situacao = %s")
        params.append(filtros["situacao"])
    if filtros.get("pagamento") == "SEM":
        condicoes.append("pg.id IS NULL")
    elif filtros.get("pagamento"):
        condicoes.append("pg.situacao = %s")
        params.append(filtros["pagamento"])
    termo = filtros.get("q")
    if termo:
        if termo.isdigit() and len(termo) <= 9:
            condicoes.append("(p.numero = %s OR c.documento LIKE %s)")
            params.extend([int(termo), f"%{termo}%"])
        else:
            condicoes.append("c.nome ILIKE %s")
            params.append(f"%{util.escapar_like(termo)}%")
    return (" WHERE " + " AND ".join(condicoes)) if condicoes else "", params


def listar(filtros, limite, deslocamento):
    """Retorna (linhas, total) para a lista de pagamentos."""
    onde, params = _filtro(filtros)
    total = db.um("SELECT count(*) AS total " + _BASE + onde, params)["total"]
    linhas = db.todos(
        """SELECT p.numero, p.situacao, p.autorizacao, p.criado_em, p.atualizado_em,
                  c.nome AS cliente_nome, c.categoria,
                  pg.valor, pg.forma, pg.situacao AS pagamento_situacao,
                  pg.criado_em AS cobranca_em, pg.data_confirmacao,
                  (SELECT count(*) FROM public.placa pl WHERE pl.pedido_numero = p.numero) AS placas
           """ + _BASE + onde + " ORDER BY p.numero DESC LIMIT %s OFFSET %s",
        params + [limite, deslocamento],
    )
    return linhas, total


def buscar_pedido(numero):
    return db.um(
        """SELECT p.numero, p.situacao, p.autorizacao, p.criado_em, p.atualizado_em, p.motivo,
                  c.id AS cliente_id, c.nome AS cliente_nome, c.documento, c.categoria
           FROM public.pedido p JOIN public.cliente c ON c.id = p.cliente_id
           WHERE p.numero = %s""",
        (numero,),
    )


def placas(numero):
    """Placas do pedido com o modelo e o saldo atual do estoque."""
    return db.todos(
        """SELECT pl.id, pl.posicao, pl.numero_placa, pl.item_estoque_id,
                  e.modelo, e.quantidade AS saldo
           FROM public.placa pl JOIN public.item_estoque e ON e.id = pl.item_estoque_id
           WHERE pl.pedido_numero = %s ORDER BY pl.posicao""",
        (numero,),
    )


def pagamento(numero):
    return db.um(
        """SELECT id, valor, forma, situacao, data_confirmacao, criado_em
           FROM public.pagamento WHERE pedido_numero = %s""",
        (numero,),
    )


def gerar_cobranca(numero, valor):
    db.executar("CALL public.sp_gerar_cobranca(%s, %s, %s)", (numero, valor, FORMA_PIX))


def confirmar_pagamento(numero):
    db.executar("CALL public.sp_confirmar_pagamento(%s)", (numero,))


def finalizar(numero):
    """Finaliza (baixa o estoque pela procedure) e gera avisos de estoque na mesma transacao."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("CALL public.sp_finalizar_pedido(%s)", (numero,))
            cur.execute("CALL public.sp_gerar_avisos_estoque()")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
