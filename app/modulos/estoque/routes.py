"""UC10 Gerenciar estoque (Jonathan). Somente administrador.

Entrada e ajustes -> sp_movimentar_estoque (o banco recusa saldo negativo).
Saida de placas acontece apenas na finalizacao do pedido (sp_finalizar_pedido).
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.modulos.pagamentos import comum
from app.seguranca import perfil_required
from . import repo

bp = Blueprint("estoque", __name__, url_prefix="/estoque", template_folder="templates", static_folder="static")

POR_PAGINA = 20
QTD_MAXIMA = 100_000
# SAIDA fica de fora: e registrada pela procedure de finalizacao, ligada ao pedido.
TIPOS_MANUAIS = {t: comum.MOVIMENTACOES[t] for t in ("ENTRADA", "AJUSTE_ENTRADA", "AJUSTE_SAIDA")}


@bp.context_processor
def _contexto():
    return {"estados": comum.ESTADOS_ESTOQUE, "selo_estoque": comum.SELO_ESTOQUE,
            "movimentacoes_rotulo": comum.MOVIMENTACOES, "tipos_manuais": TIPOS_MANUAIS}


def _inteiro(texto, minimo, maximo):
    texto = (texto or "").strip()
    if not texto.isdigit():
        return None
    valor = int(texto)
    return valor if minimo <= valor <= maximo else None


def _flash_erro_banco(exc):
    mensagem = comum.mensagem_erro(exc)
    if mensagem is None:
        raise exc
    flash(mensagem, "erro")


def _item_ou_404(item_id):
    item = repo.buscar(item_id)
    if item is None:
        abort(404)
    return item


def _resumo(itens):
    return {
        "modelos": len(itens),
        "unidades": sum(i["quantidade"] for i in itens),
        "minimo": sum(1 for i in itens if i["estado"] == "NIVEL_MINIMO"),
        "esgotados": sum(1 for i in itens if i["estado"] == "ESGOTADO"),
    }


def _pagina_lista(dados=None, erros=None, abrir_novo=False):
    itens = repo.listar()
    return render_template(
        "estoque/lista.html", itens=itens, resumo=_resumo(itens), avisos=repo.avisos_nao_lidos(),
        dados=dados or {"nivel_minimo": "0", "quantidade": "0"}, erros=erros or {}, abrir_novo=abrir_novo,
    )


@bp.route("/")
@perfil_required("ADMINISTRADOR")
def index():
    return _pagina_lista()


@bp.route("/novo", methods=["POST"])
@perfil_required("ADMINISTRADOR")
def novo():
    dados = {c: (request.form.get(c) or "").strip() for c in ("modelo", "nivel_minimo", "quantidade")}
    dados["modelo"] = " ".join(dados["modelo"].split())
    erros = {}
    if not 3 <= len(dados["modelo"]) <= 60:
        erros["modelo"] = "Informe o nome do modelo (3 a 60 caracteres)."
    minimo = _inteiro(dados["nivel_minimo"], 0, QTD_MAXIMA)
    if minimo is None:
        erros["nivel_minimo"] = f"Informe um número inteiro de 0 a {QTD_MAXIMA}."
    quantidade = _inteiro(dados["quantidade"] or "0", 0, QTD_MAXIMA)
    if quantidade is None:
        erros["quantidade"] = f"Informe um número inteiro de 0 a {QTD_MAXIMA}."
    if not erros:
        try:
            item_id = repo.criar_modelo(dados["modelo"], minimo, quantidade)
        except Exception as exc:
            mensagem = comum.mensagem_erro(exc)
            if mensagem is None:
                raise
            restricao = getattr(getattr(exc, "diag", None), "constraint_name", None)
            erros["modelo" if restricao == "uk_item_modelo" else "_geral"] = mensagem
        else:
            flash(f"Modelo \"{dados['modelo']}\" cadastrado" + (f" com entrada de {quantidade} unidade(s)." if quantidade else "."), "ok")
            return redirect(url_for("estoque.item", item_id=item_id))
    return _pagina_lista(dados, erros, abrir_novo=True), 200


@bp.route("/<int:item_id>")
@perfil_required("ADMINISTRADOR")
def item(item_id):
    registro = _item_ou_404(item_id)
    pagina = max(request.args.get("page", 1, type=int), 1)
    linhas, total = repo.movimentacoes(item_id, POR_PAGINA, (pagina - 1) * POR_PAGINA)
    paginas = max((total + POR_PAGINA - 1) // POR_PAGINA, 1)
    if pagina > paginas:
        return redirect(url_for("estoque.item", item_id=item_id, page=paginas))
    avisos = [a for a in repo.avisos_nao_lidos() if a["item_estoque_id"] == item_id]
    return render_template("estoque/item.html", item=registro, movimentacoes=linhas, total=total,
                           pagina=pagina, paginas=paginas, avisos=avisos, qtd_maxima=QTD_MAXIMA)


@bp.route("/<int:item_id>/movimentar", methods=["POST"])
@perfil_required("ADMINISTRADOR")
def movimentar(item_id):
    _item_ou_404(item_id)
    tipo = request.form.get("tipo", "")
    quantidade = _inteiro(request.form.get("quantidade"), 1, QTD_MAXIMA)
    if tipo not in TIPOS_MANUAIS:
        flash("Escolha entrada, ajuste para mais ou ajuste para menos.", "erro")
    elif quantidade is None:
        flash(f"Informe uma quantidade inteira de 1 a {QTD_MAXIMA}.", "erro")
    else:
        try:
            repo.movimentar(item_id, tipo, quantidade)
        except Exception as exc:
            _flash_erro_banco(exc)
        else:
            flash(f"{TIPOS_MANUAIS[tipo]} de {quantidade} unidade(s) registrada.", "ok")
    return redirect(url_for("estoque.item", item_id=item_id))


@bp.route("/<int:item_id>/minimo", methods=["POST"])
@perfil_required("ADMINISTRADOR")
def minimo(item_id):
    _item_ou_404(item_id)
    valor = _inteiro(request.form.get("nivel_minimo"), 0, QTD_MAXIMA)
    if valor is None:
        flash(f"Informe um nível mínimo inteiro de 0 a {QTD_MAXIMA}.", "erro")
    else:
        try:
            repo.definir_minimo(item_id, valor)
        except Exception as exc:
            _flash_erro_banco(exc)
        else:
            flash(f"Nível mínimo atualizado para {valor}.", "ok")
    return redirect(url_for("estoque.item", item_id=item_id))
