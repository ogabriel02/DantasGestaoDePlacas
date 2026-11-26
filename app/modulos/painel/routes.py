"""UC12 Painel e avisos (Jonathan).

Pagina inicial apos o login: cartoes por situacao, avisos e pedidos parados.
Rotina do ator Tempo: comando "flask --app run painel gerar-avisos" (Agendador de Tarefas)
ou botao "Gerar avisos agora" (administrador).
"""
import click
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from app.modulos.pagamentos import comum
from app.seguranca import login_required, perfil_required
from . import avisos as rotina
from . import repo

bp = Blueprint("painel", __name__, url_prefix="", template_folder="templates", static_folder="static",
               static_url_path="/painel/static")

ADMIN = "ADMINISTRADOR"
TIPOS_AVISO = {"PEDIDO_PARADO": "Pedido parado", "ESTOQUE_MINIMO": "Estoque no mínimo", "ESTOQUE_ESGOTADO": "Estoque esgotado"}
SELO_AVISO = {"PEDIDO_PARADO": "alerta", "ESTOQUE_MINIMO": "alerta", "ESTOQUE_ESGOTADO": "erro"}


def _admin():
    return g.usuario["perfil"] == ADMIN


def _resumo_texto(resultado):
    return (f"Rotina executada: {resultado['pedidos']} aviso(s) de pedido parado e "
            f"{resultado['estoque']} de estoque gerado(s).")


@bp.route("/")
@login_required
def index():
    dias = rotina.dias_parado()
    todos = request.args.get("avisos") == "todos"
    contagem = repo.contagem_por_situacao()
    cartoes = [{"situacao": s, "rotulo": r, "total": contagem.get(s, 0), "tipo": comum.SELO_SITUACAO[s]}
               for s, r in comum.SITUACOES.items()]
    abertos = sum(contagem.get(s, 0) for s in ("CRIADO", "AGUARDANDO_PAGAMENTO", "EM_PRODUCAO"))
    return render_template(
        "painel/index.html", cartoes=cartoes, abertos=abertos, dias=dias, todos=todos,
        avisos=repo.avisos(incluir_estoque=_admin(), incluir_lidos=todos),
        parados=repo.pedidos_parados(dias), estoque=repo.estado_estoque() if _admin() else None,
        tipos_aviso=TIPOS_AVISO, selo_aviso=SELO_AVISO, situacoes=comum.SITUACOES,
        selo_situacao=comum.SELO_SITUACAO, estados=comum.ESTADOS_ESTOQUE,
    )


@bp.route("/avisos/<int:aviso_id>/lido", methods=["POST"])
@login_required
def marcar_lido(aviso_id):
    aviso = repo.buscar_aviso(aviso_id)
    if aviso is None:
        abort(404)
    if aviso["item_estoque_id"] is not None and not _admin():
        abort(403)  # aviso de estoque e assunto do administrador
    if repo.marcar_lido(aviso_id):
        flash("Aviso marcado como lido.", "ok")
    else:
        flash("Este aviso já estava marcado como lido.", "info")
    return redirect(url_for("painel.index"))


@bp.route("/avisos/gerar", methods=["POST"])
@perfil_required(ADMIN)
def gerar_avisos():
    try:
        resultado = rotina.gerar()
    except Exception as exc:
        mensagem = comum.mensagem_erro(exc)
        if mensagem is None:
            raise
        flash(mensagem, "erro")
    else:
        flash(_resumo_texto(resultado), "ok")
    return redirect(url_for("painel.index"))


@bp.cli.command("gerar-avisos")
@click.option("--dias", type=click.IntRange(1, 365), default=None,
              help="Dias sem atualização para considerar o pedido parado (padrão: DIAS_PEDIDO_PARADO do .env ou 3).")
def gerar_avisos_cli(dias):
    """Ator Tempo: gera avisos de pedidos parados e de estoque baixo."""
    click.echo(_resumo_texto(rotina.gerar(dias)))
