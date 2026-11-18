"""Consultas parametrizadas e procedures do DGP_PostgreSQL entregue."""
from app import db, util

BASE = '''FROM public.pedido p JOIN public.cliente c ON c.id=p.cliente_id
          JOIN public.veiculo v ON v.id=p.veiculo_id'''

def buscar_cliente_por_documento(documento):
    return db.um('''SELECT id, nome, documento, categoria FROM public.cliente
        WHERE documento=%s''', (documento,))

def listar(filtros, limite, deslocamento):
    condicoes, params = [], []
    if filtros.get('situacao'):
        condicoes.append('p.situacao=%s')
        params.append(filtros['situacao'])
    if filtros.get('cliente'):
        condicoes.append('(c.nome ILIKE %s OR c.documento ILIKE %s)')
        termo = filtros['cliente']
        params.extend([f"%{util.escapar_like(termo)}%", f"%{util.so_digitos(termo) or util.escapar_like(termo)}%"])
    if filtros.get('chassi'):
        condicoes.append('v.chassi ILIKE %s')
        params.append(f"%{util.escapar_like(filtros['chassi'])}%")
    if filtros.get('data'):
        condicoes.append('p.criado_em::date=%s::date')
        params.append(filtros['data'])
    onde = ' WHERE ' + ' AND '.join(condicoes) if condicoes else ''
    total = db.um('SELECT count(*) AS total ' + BASE + onde, params)['total']
    linhas = db.todos('''SELECT p.*, c.nome AS cliente_nome, c.categoria, v.chassi,
        (SELECT string_agg(pl.numero_placa || ' · ' || e.modelo || ' · ' || lower(pl.posicao), ', ' ORDER BY pl.posicao)
         FROM public.placa pl JOIN public.item_estoque e ON e.id=pl.item_estoque_id WHERE pl.pedido_numero=p.numero) AS placas,
        (SELECT pg.situacao FROM public.pagamento pg WHERE pg.pedido_numero=p.numero) AS pagamento
        ''' + BASE + onde + ' ORDER BY p.numero DESC LIMIT %s OFFSET %s', params + [limite, deslocamento])
    return linhas, total

def buscar(numero):
    return db.um('''SELECT p.*, c.nome AS cliente_nome, c.categoria, c.documento, c.telefone,
        v.chassi, u.nome AS usuario_nome ''' + BASE + ''' JOIN public.usuario u ON u.id=p.usuario_id
        WHERE p.numero=%s''', (numero,))

def placas(numero):
    return db.todos('''SELECT pl.*, e.modelo FROM public.placa pl
        JOIN public.item_estoque e ON e.id=pl.item_estoque_id
        WHERE pl.pedido_numero=%s ORDER BY pl.posicao''', (numero,))

def pagamento(numero):
    return db.um('SELECT * FROM public.pagamento WHERE pedido_numero=%s', (numero,))

def modelos():
    return db.todos('SELECT id, modelo, quantidade FROM public.item_estoque ORDER BY modelo')

def criar(dados, usuario_id):
    # db.executar confirma cada chamada; aqui precisamos de um único commit.
    conn = db.get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute('''INSERT INTO public.veiculo (chassi) VALUES (%s)
                ON CONFLICT (chassi) DO UPDATE SET chassi=EXCLUDED.chassi RETURNING id''', (dados['chassi'],))
            veiculo = cur.fetchone()['id']
            cur.execute('CALL public.sp_criar_pedido(%s, %s, %s, %s, %s)',
                        (dados['cliente_id'], usuario_id, veiculo, dados['observacoes'] or None, None))
            numero = cur.fetchone()['p_numero']
            for posicao in ('DIANTEIRA', 'TRASEIRA'):
                if dados['posicao'] in (posicao, 'PAR'):
                    cur.execute('CALL public.sp_adicionar_placa(%s, %s, %s, %s, %s, %s, %s)',
                                (numero, dados['item_id'], posicao, dados['numero_placa'],
                                 dados['qr_' + posicao.lower()], dados['cor_placa'] or None, dados['cor_caracteres']))
        conn.commit()
        return numero
    except Exception:
        conn.rollback()
        raise

def definir_autorizacao(numero, valor):
    db.executar('CALL public.sp_definir_autorizacao(%s, %s)', (numero, valor))

def cancelar(numero, motivo):
    db.executar('CALL public.sp_cancelar_pedido(%s, %s)', (numero, motivo))
