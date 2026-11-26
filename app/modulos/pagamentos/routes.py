"""UC06 Controlar pagamentos e UC07 Finalizar pedido (Jonathan).

Fluxo: pedido CRIADO -> sp_gerar_cobranca (Pix) -> AGUARDANDO_PAGAMENTO
       -> sp_confirmar_pagamento -> EM_PRODUCAO -> sp_finalizar_pedido -> FINALIZADO.
Quem decide se cada passo e permitido e o banco; a tela so orienta e mostra a recusa.
"""
from collections import Counter

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from werkzeug.routing import BuildError

from app.seguranca import login_required
from . import comum, precos, repo

bp = Blueprint("pagamentos", __name__, url_prefix="/pagamentos", template_folder="templates", static_folder="static")

POR_PAGINA = 15
FILTRO_PAGAMENTO = {"SEM": "Sem cobrança", "PENDENTE": "Pendente", "CONFIRMADO": "Confirmado"}


@bp.app_template_filter("moeda")
def _filtro_moeda(valor):
    return comum.formatar_moeda(valor)


@bp.context_processor
def _contexto():
    return {
        "situacoes": comum.SITUACOES, "selo_situacao": comum.SELO_SITUACAO,
        "autorizacoes": comum.AUTORIZACOES, "pagamentos_rotulo": comum.PAGAMENTOS,
        "selo_pagamento": comum.SELO_PAGAMENTO,
    }


def _url_pedido(numero):
    """Link para o detalhe do modulo Pedidos (Tatiane), se ele ja estiver instalado."""
    try:
        return url_for("pedidos.ver", numero=numero)
    except BuildError:
        return None


def _flash_erro_banco(exc):
    mensagem = comum.mensagem_erro(exc)
    if mensagem is None:
        raise exc
    flash(mensagem, "erro")


def _pedido_ou_404(numero):
    pedido = repo.buscar_pedido(numero)
    if pedido is None:
        abort(404)
    return pedido


def requisitos_finalizacao(pedido, placas):
    """Checklist apenas informativo; a decisao final e de sp_finalizar_pedido."""
    por_item = Counter(p["item_estoque_id"] for p in placas)
    saldos = {p["item_estoque_id"]: (p["modelo"], p["saldo"]) for p in placas}
    faltando = [f"{saldos[i][0]} (saldo {saldos[i][1]}, precisa {qtd})"
                for i, qtd in por_item.items() if saldos[i][1] < qtd]
    return [
        {"ok": pedido["situacao"] == "EM_PRODUCAO", "texto": "Pagamento confirmado (pedido em produção)"},
        {"ok": pedido["autorizacao"] == "LIBERADA", "texto": "Autorização externa liberada"},
        {"ok": 1 <= len(placas) <= 2, "texto": f"Uma ou duas placas no pedido (tem {len(placas)})"},
        {"ok": bool(placas) and not faltando,
         "texto": "Estoque suficiente" + (": falta " + "; ".join(faltando) if faltando else "")},
    ]


@bp.route("/")
@login_required
def index():
    filtros = {
        "situacao": request.args.get("situacao", ""),
        "pagamento": request.args.get("pagamento", ""),
        "q": (request.args.get("q") or "").strip()[:80],
    }
    if filtros["situacao"] not in comum.SITUACOES:
        filtros["situacao"] = ""
    if filtros["pagamento"] not in FILTRO_PAGAMENTO:
        filtros["pagamento"] = ""
    pagina = max(request.args.get("page", 1, type=int), 1)
    linhas, total = repo.listar(filtros, POR_PAGINA, (pagina - 1) * POR_PAGINA)
    paginas = max((total + POR_PAGINA - 1) // POR_PAGINA, 1)
    if pagina > paginas:
        return redirect(url_for("pagamentos.index", page=paginas, **{k: v for k, v in filtros.items() if v}))
    return render_template(
        "pagamentos/lista.html", pedidos=linhas, total=total, pagina=pagina, paginas=paginas,
        filtros=filtros, filtro_pagamento=FILTRO_PAGAMENTO,
        args_paginacao={k: v for k, v in filtros.items() if v},
    )


@bp.route("/pedido/<int:numero>")
@login_required
def pedido(numero):
    ped = _pedido_ou_404(numero)
    placas = repo.placas(numero)
    descricao, valor = precos.calcular(placas)
    return render_template(
        "pagamentos/pedido.html", pedido=ped, placas=placas, pagamento=repo.pagamento(numero),
        descricao_preco=descricao, valor=valor, tabela_precos=precos.TABELA.values(),
        requisitos=requisitos_finalizacao(ped, placas), url_pedido=_url_pedido(numero),
    )


@bp.route("/pedido/<int:numero>/cobranca", methods=["POST"])
@login_required
def gerar_cobranca(numero):
    _pedido_ou_404(numero)
    placas = repo.placas(numero)
    descricao, valor = precos.calcular(placas)
    if valor is None:
        flash("O pedido precisa ter uma placa (individual) ou duas (par) para gerar a cobrança.", "erro")
    else:
        try:
            repo.gerar_cobranca(numero, valor)
        except Exception as exc:
            _flash_erro_banco(exc)
        else:
            flash(f"Cobrança Pix de {comum.formatar_moeda(valor)} ({descricao.lower()}) gerada. Aguardando pagamento.", "ok")
    return redirect(url_for("pagamentos.pedido", numero=numero))


@bp.route("/pedido/<int:numero>/confirmar", methods=["POST"])
@login_required
def confirmar(numero):
    _pedido_ou_404(numero)
    try:
        repo.confirmar_pagamento(numero)
    except Exception as exc:
        _flash_erro_banco(exc)
    else:
        flash("Pagamento confirmado. O pedido seguiu para produção.", "ok")
    return redirect(url_for("pagamentos.pedido", numero=numero))


@bp.route("/pedido/<int:numero>/finalizar", methods=["POST"])
@login_required
def finalizar(numero):
    _pedido_ou_404(numero)
    try:
        repo.finalizar(numero)
    except Exception as exc:
        _flash_erro_banco(exc)
    else:
        flash("Pedido finalizado. As placas foram baixadas do estoque.", "ok")
    return redirect(url_for("pagamentos.pedido", numero=numero))
