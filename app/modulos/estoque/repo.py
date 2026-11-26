"""UC10 Gerenciar estoque: consultas e gravacoes.

Saldo so muda por sp_movimentar_estoque (o trigger do banco atualiza item_estoque.quantidade).
Nivel minimo e cadastro de modelo usam as colunas liberadas pelo 04_permissoes_aplicacao.sql
(INSERT/UPDATE de modelo e nivel_minimo); nao ha procedure para eles.
Depois de cada alteracao, sp_gerar_avisos_estoque roda na mesma transacao.
"""
from app import db

_EM_ABERTO = "('CRIADO','AGUARDANDO_PAGAMENTO','EM_PRODUCAO')"


def listar():
    return db.todos(
        f"""SELECT e.id, e.modelo, e.quantidade, e.nivel_minimo, e.estado, e.atualizado_em,
                   (SELECT count(*) FROM public.placa pl JOIN public.pedido p ON p.numero = pl.pedido_numero
                     WHERE pl.item_estoque_id = e.id AND p.situacao IN {_EM_ABERTO}) AS em_pedidos
            FROM public.vw_estado_estoque e ORDER BY e.modelo"""
    )


def buscar(item_id):
    return db.um(
        f"""SELECT e.id, e.modelo, e.quantidade, e.nivel_minimo, e.estado, e.criado_em, e.atualizado_em,
                   (SELECT count(*) FROM public.placa pl JOIN public.pedido p ON p.numero = pl.pedido_numero
                     WHERE pl.item_estoque_id = e.id AND p.situacao IN {_EM_ABERTO}) AS em_pedidos
            FROM public.vw_estado_estoque e WHERE e.id = %s""",
        (item_id,),
    )


def movimentacoes(item_id, limite, deslocamento):
    total = db.um("SELECT count(*) AS total FROM public.movimentacao_estoque WHERE item_estoque_id = %s", (item_id,))["total"]
    linhas = db.todos(
        """SELECT id, data, tipo, quantidade, pedido_numero FROM public.movimentacao_estoque
           WHERE item_estoque_id = %s ORDER BY data DESC, id DESC LIMIT %s OFFSET %s""",
        (item_id, limite, deslocamento),
    )
    return linhas, total


def avisos_nao_lidos():
    return db.todos(
        """SELECT a.id, a.tipo, a.mensagem, a.data, a.item_estoque_id, e.modelo
           FROM public.aviso a JOIN public.item_estoque e ON e.id = a.item_estoque_id
           WHERE NOT a.lido ORDER BY a.data DESC, a.id DESC"""
    )


def _com_avisos(sql, params):
    """Executa o comando e sp_gerar_avisos_estoque com um unico commit."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cur.execute("CALL public.sp_gerar_avisos_estoque()")
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def movimentar(item_id, tipo, quantidade):
    _com_avisos("CALL public.sp_movimentar_estoque(%s, %s, %s)", (item_id, tipo, quantidade))


def definir_minimo(item_id, nivel_minimo):
    _com_avisos("UPDATE public.item_estoque SET nivel_minimo = %s WHERE id = %s", (nivel_minimo, item_id))


def criar_modelo(modelo, nivel_minimo, quantidade_inicial):
    """Cadastra com saldo zero (exigencia do banco) e registra a ENTRADA inicial, se houver."""
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO public.item_estoque (modelo, nivel_minimo) VALUES (%s, %s) RETURNING id",
                        (modelo, nivel_minimo))
            item_id = cur.fetchone()["id"]
            if quantidade_inicial:
                cur.execute("CALL public.sp_movimentar_estoque(%s, %s, %s)", (item_id, "ENTRADA", quantidade_inicial))
            cur.execute("CALL public.sp_gerar_avisos_estoque()")
        conn.commit()
        return item_id
    except Exception:
        conn.rollback()
        raise
