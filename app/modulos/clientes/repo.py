from app import db, util

COLUNAS = ["tipo_pessoa", "categoria", "documento", "nome", "cep", "rua", "numero",
           "bairro", "cidade", "uf", "complemento", "telefone", "email"]


def _filtro(busca, categoria):
    condicoes, params = [], []
    if busca:
        parte = "c.nome ILIKE %s"
        params.append(f"%{util.escapar_like(busca)}%")
        digitos = util.so_digitos(busca)
        if digitos:
            parte += " OR c.documento LIKE %s"
            params.append(f"%{digitos}%")
        condicoes.append(f"({parte})")
    if categoria:
        condicoes.append("c.categoria = %s")
        params.append(categoria)
    onde = ("WHERE " + " AND ".join(condicoes)) if condicoes else ""
    return onde, params


def listar(busca, categoria, limite, deslocamento):
    """Retorna (linhas, total) para a tela de clientes."""
    onde, params = _filtro(busca, categoria)
    total = db.um(f"SELECT count(*) AS total FROM cliente c {onde}", params)["total"]
    linhas = db.todos(
        f"""SELECT c.id, c.tipo_pessoa, c.categoria, c.documento, c.nome, c.telefone,
                   c.bairro, c.cidade, c.uf, c.email,
                   (SELECT count(*) FROM pedido p WHERE p.cliente_id = c.id) AS pedidos
            FROM cliente c {onde}
            ORDER BY c.nome
            LIMIT %s OFFSET %s""",
        params + [limite, deslocamento],
    )
    return linhas, total


def buscar(cliente_id):
    return db.um(
        f"""SELECT id, {", ".join(COLUNAS)},
                   (SELECT count(*) FROM pedido p WHERE p.cliente_id = cliente.id) AS pedidos
            FROM cliente WHERE id = %s""",
        (cliente_id,),
    )


def buscar_para_selecao(termo, limite=10):
    """Uso do UC04 (Registrar pedido): procura cliente por nome ou documento."""
    linhas, _ = listar(termo, "", limite, 0)
    return linhas


def criar(dados):
    linha = db.executar(
        f"""INSERT INTO cliente ({", ".join(COLUNAS)})
            VALUES ({", ".join("%(" + c + ")s" for c in COLUNAS)}) RETURNING id""",
        dados,
        retornar=True,
    )
    return linha["id"]


def atualizar(cliente_id, dados):
    sets = ", ".join(f"{c} = %({c})s" for c in COLUNAS)
    db.executar(f"UPDATE cliente SET {sets} WHERE id = %(id)s", {**dados, "id": cliente_id})
