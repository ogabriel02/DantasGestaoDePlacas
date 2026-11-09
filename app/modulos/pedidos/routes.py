"""Pedidos - responsavel: Tatiane (UC04, UC05, UC08, UC09).

Substitua este arquivo pela implementacao real. Mantenha:
  - o blueprint chamado "pedidos" e a rota "index" (o menu lateral usa isso);
  - os templates dentro de app/modulos/pedidos/templates/pedidos/.
Use app.db (todos, um, executar) e as procedures sp_* do banco.
"""
from flask import Blueprint, render_template

from app.seguranca import login_required

bp = Blueprint("pedidos", __name__, url_prefix="/pedidos")


@bp.route("/")
@login_required
def index():
    return render_template(
        "em_construcao.html", titulo="Pedidos", responsavel="Tatiane", ucs="UC04, UC05, UC08, UC09", modulo="pedidos"
    )
