"""UC01 Autenticar (Gabriel)."""
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from app import menu, seguranca
from . import repo

bp = Blueprint("autenticacao", __name__, template_folder="templates")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(menu.url_inicial())

    destino = request.values.get("next", "")
    erro = None

    if request.method == "POST":
        digitado = (request.form.get("login") or "").strip().lower()[:60]
        senha = (request.form.get("senha") or "")[:128]
        chave = f"{request.remote_addr}|{digitado}"

        espera = seguranca.segundos_bloqueado(chave)
        if espera:
            erro = f"Muitas tentativas. Aguarde cerca de {max(espera // 60, 1)} min e tente de novo."
        else:
            usuario = repo.buscar_por_login(digitado) if digitado else None
            senha_ok = seguranca.verificar_senha(senha, usuario["senha_hash"] if usuario else seguranca.HASH_FALSO)
            if usuario and senha_ok and usuario["ativo"]:
                seguranca.limpar_falhas(chave)
                session.clear()  # evita fixacao de sessao
                session["usuario_id"] = usuario["id"]
                session.permanent = True
                return redirect(seguranca.destino_seguro(destino) or menu.url_inicial())
            seguranca.registrar_falha(chave)
            erro = "Login ou senha inválidos, ou usuário inativo."

    return render_template("autenticacao/login.html", erro=erro, destino=destino)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Você saiu do sistema.", "ok")
    return redirect(url_for("autenticacao.login"))
