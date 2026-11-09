"""UC02 Gerenciar usuarios (Gabriel). Somente administrador."""
import re

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app import db, seguranca, util
from app.seguranca import perfil_required
from . import repo

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios", template_folder="templates")

LOGIN_RE = re.compile(r"^[a-z0-9._-]{3,60}$")


def _validar(form, criando, proprio_id=None):
    """Valida o formulario. Retorna (dados, erros)."""
    dados = {
        "nome": (form.get("nome") or "").strip(),
        "login": (form.get("login") or "").strip().lower(),
        "perfil": (form.get("perfil") or "").strip(),
        "senha": form.get("senha") or "",
        "confirmar": form.get("confirmar") or "",
    }
    erros = {}
    if not 3 <= len(dados["nome"]) <= 120:
        erros["nome"] = "Informe o nome (3 a 120 caracteres)."
    if not LOGIN_RE.match(dados["login"]):
        erros["login"] = "Use 3 a 60 caracteres: letras minúsculas, números, ponto, hífen ou sublinhado."
    if dados["perfil"] not in util.PERFIS:
        erros["perfil"] = "Escolha um perfil."
    if criando or dados["senha"]:
        if len(dados["senha"]) < 8 or len(dados["senha"]) > 128:
            erros["senha"] = "A senha deve ter de 8 a 128 caracteres."
        elif dados["senha"] != dados["confirmar"]:
            erros["confirmar"] = "A confirmação não confere com a senha."
    return dados, erros


@bp.route("/")
@perfil_required("ADMINISTRADOR")
def index():
    return render_template("usuarios/lista.html", usuarios=repo.listar())


@bp.route("/novo", methods=["GET", "POST"])
@perfil_required("ADMINISTRADOR")
def novo():
    dados, erros = {"perfil": "FUNCIONARIO"}, {}
    if request.method == "POST":
        dados, erros = _validar(request.form, criando=True)
        if not erros:
            try:
                repo.criar(dados["nome"], dados["login"], seguranca.gerar_hash(dados["senha"]), dados["perfil"])
            except Exception as exc:
                erro = db.traduzir_erro(exc)
                if erro is None:
                    raise
                erros[erro.campo or "_geral"] = erro.mensagem
            else:
                flash("Usuário cadastrado com sucesso.", "ok")
                return redirect(url_for("usuarios.index"))
    return render_template("usuarios/form.html", dados=dados, erros=erros, editando=False, proprio=False)


@bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@perfil_required("ADMINISTRADOR")
def editar(usuario_id):
    atual = repo.buscar(usuario_id)
    if atual is None:
        abort(404)
    proprio = atual["id"] == g.usuario["id"]
    dados, erros = dict(atual), {}
    if request.method == "POST":
        dados, erros = _validar(request.form, criando=False)
        if proprio:
            dados["perfil"] = atual["perfil"]  # ninguem altera o proprio perfil
            erros.pop("perfil", None)
        if not erros:
            novo_hash = seguranca.gerar_hash(dados["senha"]) if dados["senha"] else None
            try:
                repo.atualizar(usuario_id, dados["nome"], dados["login"], dados["perfil"], novo_hash)
            except Exception as exc:
                erro = db.traduzir_erro(exc)
                if erro is None:
                    raise
                erros[erro.campo or "_geral"] = erro.mensagem
            else:
                flash("Usuário atualizado com sucesso.", "ok")
                return redirect(url_for("usuarios.index"))
    return render_template("usuarios/form.html", dados=dados, erros=erros, editando=True, proprio=proprio, usuario_id=usuario_id)


@bp.route("/<int:usuario_id>/status", methods=["POST"])
@perfil_required("ADMINISTRADOR")
def alterar_status(usuario_id):
    alvo = repo.buscar(usuario_id)
    if alvo is None:
        abort(404)
    if alvo["id"] == g.usuario["id"]:
        flash("Você não pode inativar a sua própria conta.", "erro")
    else:
        ativar = not alvo["ativo"]
        repo.definir_ativo(usuario_id, ativar)
        flash("Usuário reativado." if ativar else "Usuário inativado. Ele não consegue mais entrar no sistema.", "ok")
    return redirect(url_for("usuarios.index"))
