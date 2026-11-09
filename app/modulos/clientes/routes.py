"""UC03 Gerenciar clientes e despachantes (Gabriel)."""
import re

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app import db, util
from app.seguranca import login_required
from . import repo

bp = Blueprint("clientes", __name__, url_prefix="/clientes", template_folder="templates")

POR_PAGINA = 15
UFS_OPCOES = [(u, u) for u in util.UFS]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
LIMITES = {"nome": 120, "rua": 100, "numero": 10, "bairro": 60, "cidade": 60, "complemento": 60, "email": 120}


def _validar(form, atual=None):
    """Valida e normaliza o formulario. Retorna (dados, erros)."""
    bruto = {c: (form.get(c) or "").strip() for c in repo.COLUNAS}
    dados = dict(bruto)
    dados["tipo_pessoa"] = bruto["tipo_pessoa"].upper()
    dados["categoria"] = bruto["categoria"].upper()
    dados["documento"] = util.so_digitos(bruto["documento"])
    dados["cep"] = util.so_digitos(bruto["cep"])
    dados["telefone"] = util.so_digitos(bruto["telefone"])
    dados["uf"] = bruto["uf"].upper()
    dados["email"] = bruto["email"].lower()
    dados["complemento"] = bruto["complemento"] or None

    erros = {}
    if dados["tipo_pessoa"] not in util.TIPOS_PESSOA:
        erros["tipo_pessoa"] = "Escolha pessoa física ou jurídica."
    if dados["categoria"] not in util.CATEGORIAS:
        erros["categoria"] = "Escolha particular ou despachante."

    tamanho = {"PF": 11, "PJ": 14}.get(dados["tipo_pessoa"])
    if tamanho and len(dados["documento"]) != tamanho:
        erros["documento"] = "O CPF deve ter 11 dígitos." if tamanho == 11 else "O CNPJ deve ter 14 dígitos."
    elif tamanho and current_app.config.get("VALIDAR_DIGITO_DOCUMENTO", True):
        mudou = atual is None or atual["documento"] != dados["documento"]
        valido = util.validar_cpf(dados["documento"]) if tamanho == 11 else util.validar_cnpj(dados["documento"])
        if mudou and not valido:
            erros["documento"] = "CPF inválido." if tamanho == 11 else "CNPJ inválido."

    if not 3 <= len(dados["nome"]) <= LIMITES["nome"]:
        erros["nome"] = "Informe o nome (3 a 120 caracteres)."
    if len(dados["cep"]) != 8:
        erros["cep"] = "O CEP deve ter 8 dígitos."
    for campo, rotulo in (("rua", "a rua"), ("numero", "o número"), ("bairro", "o bairro"), ("cidade", "a cidade")):
        if not dados[campo] or len(dados[campo]) > LIMITES[campo]:
            erros[campo] = f"Informe {rotulo} (até {LIMITES[campo]} caracteres)."
    if dados["uf"] not in util.UFS:
        erros["uf"] = "Escolha o estado."
    if dados["complemento"] and len(dados["complemento"]) > LIMITES["complemento"]:
        erros["complemento"] = "No máximo 60 caracteres."
    if len(dados["telefone"]) not in (10, 11):
        erros["telefone"] = "Informe o telefone com DDD (10 ou 11 dígitos)."
    if not EMAIL_RE.match(dados["email"]) or len(dados["email"]) > LIMITES["email"]:
        erros["email"] = "Informe um e-mail válido."
    return dados, erros


@bp.route("/")
@login_required
def index():
    busca = (request.args.get("q") or "").strip()[:80]
    categoria = request.args.get("categoria", "")
    if categoria not in util.CATEGORIAS:
        categoria = ""
    pagina = max(request.args.get("page", 1, type=int), 1)
    linhas, total = repo.listar(busca, categoria, POR_PAGINA, (pagina - 1) * POR_PAGINA)
    paginas = max((total + POR_PAGINA - 1) // POR_PAGINA, 1)
    if pagina > paginas:
        return redirect(url_for("clientes.index", q=busca or None, categoria=categoria or None, page=paginas))
    return render_template(
        "clientes/lista.html", clientes=linhas, total=total, busca=busca,
        categoria=categoria, pagina=pagina, paginas=paginas,
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    dados, erros = {"tipo_pessoa": "PF", "categoria": "PARTICULAR", "uf": "MG"}, {}
    if request.method == "POST":
        dados, erros = _validar(request.form)
        if not erros:
            try:
                novo_id = repo.criar(dados)
            except Exception as exc:
                erro = db.traduzir_erro(exc)
                if erro is None:
                    raise
                erros[erro.campo or "_geral"] = erro.mensagem
            else:
                flash("Cadastro realizado com sucesso.", "ok")
                return redirect(url_for("clientes.ver", cliente_id=novo_id))
    return render_template("clientes/form.html", dados=dados, erros=erros, editando=False, ufs_opcoes=UFS_OPCOES)


@bp.route("/<int:cliente_id>")
@login_required
def ver(cliente_id):
    cliente = repo.buscar(cliente_id)
    if cliente is None:
        abort(404)
    return render_template("clientes/detalhe.html", c=cliente)


@bp.route("/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
def editar(cliente_id):
    atual = repo.buscar(cliente_id)
    if atual is None:
        abort(404)
    dados, erros = dict(atual), {}
    if request.method == "POST":
        dados, erros = _validar(request.form, atual)
        if not erros:
            try:
                repo.atualizar(cliente_id, dados)
            except Exception as exc:
                erro = db.traduzir_erro(exc)
                if erro is None:
                    raise
                erros[erro.campo or "_geral"] = erro.mensagem
            else:
                flash("Cadastro atualizado com sucesso.", "ok")
                return redirect(url_for("clientes.ver", cliente_id=cliente_id))
    return render_template("clientes/form.html", dados=dados, erros=erros, editando=True, cliente_id=cliente_id, ufs_opcoes=UFS_OPCOES)
