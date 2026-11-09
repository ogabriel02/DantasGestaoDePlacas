from app import db


def listar():
    return db.todos(
        "SELECT id, nome, login, perfil, ativo FROM usuario ORDER BY ativo DESC, nome"
    )


def buscar(usuario_id):
    return db.um(
        "SELECT id, nome, login, perfil, ativo FROM usuario WHERE id = %s", (usuario_id,)
    )


def criar(nome, login, senha_hash, perfil):
    linha = db.executar(
        "INSERT INTO usuario (nome, login, senha_hash, perfil) VALUES (%s, %s, %s, %s) RETURNING id",
        (nome, login, senha_hash, perfil),
        retornar=True,
    )
    return linha["id"]


def atualizar(usuario_id, nome, login, perfil, senha_hash=None):
    if senha_hash:
        db.executar(
            "UPDATE usuario SET nome = %s, login = %s, perfil = %s, senha_hash = %s WHERE id = %s",
            (nome, login, perfil, senha_hash, usuario_id),
        )
    else:
        db.executar(
            "UPDATE usuario SET nome = %s, login = %s, perfil = %s WHERE id = %s",
            (nome, login, perfil, usuario_id),
        )


def definir_ativo(usuario_id, ativo):
    db.executar("UPDATE usuario SET ativo = %s WHERE id = %s", (ativo, usuario_id))
