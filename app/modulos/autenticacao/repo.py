from app import db


def buscar_por_login(login):
    return db.um(
        "SELECT id, nome, login, senha_hash, perfil, ativo FROM usuario WHERE login = %s",
        (login,),
    )


def buscar_por_id(usuario_id):
    return db.um(
        "SELECT id, nome, login, perfil, ativo FROM usuario WHERE id = %s",
        (usuario_id,),
    )
