"""UC11 Emitir relatorios: somente leitura (SELECT).

Filtros comuns: periodo (data de criacao do pedido), despachante, tipo de placa
(modelo do item_estoque) e situacao do pedido.
Valores: "cobrado" = cobrancas nao canceladas; "recebido" = pagamentos CONFIRMADOS.
"""
from app import db

_DE = """FROM public.pedido p
         JOIN public.cliente c ON c.id = p.cliente_id
         LEFT JOIN public.pagamento pg ON pg.pedido_numero = p.numero
         LEFT JOIN (SELECT pedido_numero, count(*) AS n FROM public.placa GROUP BY pedido_numero) pc
                ON pc.pedido_numero = p.numero"""

_VALORES = """COALESCE(sum(pg.valor) FILTER (WHERE pg.situacao <> 'CANCELADO'), 0) AS cobrado,
              COALESCE(sum(pg.valor) FILTER (WHERE pg.situacao = 'CONFIRMADO'), 0) AS recebido"""


def _filtro(f, extra=()):
    condicoes = ["p.criado_em >= %s::date", "p.criado_em < %s::date + 1"] + list(extra)
    params = [f["inicio"], f["fim"]]
    if f.get("despachante"):
        condicoes.append("p.cliente_id = %s")
        params.append(f["despachante"])
    if f.get("item"):
        condicoes.append("EXISTS (SELECT 1 FROM public.placa x WHERE x.pedido_numero = p.numero AND x.item_estoque_id = %s)")
        params.append(f["item"])
    if f.get("situacao"):
        condicoes.append("p.situacao = %s")
        params.append(f["situacao"])
    return " WHERE " + " AND ".join(condicoes), params


def despachantes():
    return db.todos("SELECT id, nome, documento FROM public.cliente WHERE categoria = 'DESPACHANTE' ORDER BY nome")


def modelos():
    return db.todos("SELECT id, modelo FROM public.item_estoque ORDER BY modelo")


def resumo(f):
    """Uma linha por situacao do pedido."""
    onde, params = _filtro(f)
    return db.todos(
        f"""SELECT p.situacao, count(*) AS pedidos, COALESCE(sum(pc.n), 0)::int AS placas, {_VALORES}
            {_DE} {onde} GROUP BY p.situacao""",
        params,
    )


def por_despachante(f):
    onde, params = _filtro(f, ["c.categoria = 'DESPACHANTE'"])
    return db.todos(
        f"""SELECT c.id, c.nome, c.documento, count(*) AS pedidos, COALESCE(sum(pc.n), 0)::int AS placas,
                   count(*) FILTER (WHERE p.situacao = 'FINALIZADO') AS finalizados,
                   count(*) FILTER (WHERE p.situacao = 'CANCELADO') AS cancelados,
                   count(*) FILTER (WHERE p.situacao NOT IN ('FINALIZADO', 'CANCELADO')) AS em_aberto,
                   {_VALORES}
            {_DE} {onde}
            GROUP BY c.id, c.nome, c.documento ORDER BY pedidos DESC, c.nome""",
        params,
    )


def por_tipo_placa(f):
    """Placas agrupadas pelo modelo. Com filtro de tipo, conta so as placas daquele modelo."""
    onde, params = _filtro(f)
    filtro_item = ""
    if f.get("item"):
        filtro_item = " AND pl.item_estoque_id = %s"
        params = params + [f["item"]]
    return db.todos(
        f"""SELECT e.id, e.modelo, count(*) AS placas, count(DISTINCT p.numero) AS pedidos,
                   count(*) FILTER (WHERE pl.posicao = 'DIANTEIRA') AS dianteiras,
                   count(*) FILTER (WHERE pl.posicao = 'TRASEIRA') AS traseiras,
                   count(*) FILTER (WHERE p.situacao = 'FINALIZADO') AS entregues,
                   count(*) FILTER (WHERE p.situacao = 'CANCELADO') AS canceladas
            FROM public.placa pl
            JOIN public.item_estoque e ON e.id = pl.item_estoque_id
            JOIN public.pedido p ON p.numero = pl.pedido_numero
            JOIN public.cliente c ON c.id = p.cliente_id
            {onde}{filtro_item}
            GROUP BY e.id, e.modelo ORDER BY placas DESC, e.modelo""",
        params,
    )


def pedidos(f, limite):
    onde, params = _filtro(f)
    return db.todos(
        f"""SELECT p.numero, p.criado_em, p.situacao, p.autorizacao, c.nome AS cliente_nome, c.categoria, c.documento,
                   COALESCE(pc.n, 0) AS placas,
                   (SELECT string_agg(e.modelo || ' ' || lower(pl.posicao), ', ' ORDER BY pl.posicao)
                      FROM public.placa pl JOIN public.item_estoque e ON e.id = pl.item_estoque_id
                     WHERE pl.pedido_numero = p.numero) AS descricao_placas,
                   pg.valor, pg.situacao AS pagamento_situacao, pg.data_confirmacao
            {_DE} {onde}
            ORDER BY p.criado_em DESC, p.numero DESC LIMIT %s""",
        params + [limite],
    )
