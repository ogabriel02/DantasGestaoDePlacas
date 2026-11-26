"""UC12 Painel e avisos: consultas e marcacao de leitura de avisos."""
from app import db


def contagem_por_situacao():
    return {r["situacao"]: r["total"] for r in db.todos(
        "SELECT situacao, count(*) AS total FROM public.pedido GROUP BY situacao")}


def estado_estoque():
    return {r["estado"]: r["total"] for r in db.todos(
        "SELECT estado, count(*) AS total FROM public.vw_estado_estoque GROUP BY estado")}


def avisos(incluir_estoque, incluir_lidos=False, limite=50):
    """Avisos mais recentes. Funcionario nao ve avisos de estoque (area do administrador)."""
    condicoes = []
    if not incluir_estoque:
        condicoes.append("a.pedido_numero IS NOT NULL")
    if not incluir_lidos:
        condicoes.append("NOT a.lido")
    onde = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
    return db.todos(
        f"""SELECT a.id, a.tipo, a.mensagem, a.data, a.lido, a.lido_em, a.pedido_numero, a.item_estoque_id,
                   p.situacao AS pedido_situacao, e.modelo
            FROM public.aviso a
            LEFT JOIN public.pedido p ON p.numero = a.pedido_numero
            LEFT JOIN public.item_estoque e ON e.id = a.item_estoque_id
            {onde}
            ORDER BY a.lido, a.data DESC, a.id DESC LIMIT %s""",
        (limite,),
    )


def pedidos_parados(dias, limite=20):
    """Pedidos em aberto sem atualizacao ha mais de `dias` dias (calculo ao vivo)."""
    return db.todos(
        """SELECT p.numero, p.situacao, p.autorizacao, p.atualizado_em, c.nome AS cliente_nome,
                  floor(extract(epoch FROM (LOCALTIMESTAMP - p.atualizado_em)) / 86400)::int AS dias,
                  EXISTS (SELECT 1 FROM public.aviso a WHERE a.pedido_numero = p.numero
                          AND a.tipo = 'PEDIDO_PARADO' AND NOT a.lido) AS avisado
           FROM public.pedido p JOIN public.cliente c ON c.id = p.cliente_id
           WHERE p.situacao NOT IN ('FINALIZADO', 'CANCELADO')
             AND p.atualizado_em < LOCALTIMESTAMP - make_interval(days => %s)
           ORDER BY p.atualizado_em, p.numero LIMIT %s""",
        (dias, limite),
    )


def buscar_aviso(aviso_id):
    return db.um("SELECT id, tipo, lido, pedido_numero, item_estoque_id FROM public.aviso WHERE id = %s", (aviso_id,))


def marcar_lido(aviso_id):
    """Marca como lido (colunas lido/lido_em liberadas pelo 04_permissoes_aplicacao.sql)."""
    linha = db.executar(
        "UPDATE public.aviso SET lido = TRUE, lido_em = LOCALTIMESTAMP WHERE id = %s AND NOT lido RETURNING id",
        (aviso_id,), retornar=True,
    )
    return linha is not None
