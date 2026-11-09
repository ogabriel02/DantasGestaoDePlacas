"""Pagamentos - responsavel: Jonathan (UC06, UC07).

Substitua este arquivo pela implementacao real. Mantenha:
  - o blueprint chamado "pagamentos" e a rota "index" (o menu lateral usa isso);
  - os templates dentro de app/modulos/pagamentos/templates/pagamentos/.
Use app.db (todos, um, executar) e as procedures sp_* do banco.
"""
from flask import Blueprint, render_template

from app.seguranca import login_required

bp = Blueprint("pagamentos", __name__, url_prefix="/pagamentos")


@bp.route("/")
@login_required
def index():
    return render_template(
        "em_construcao.html", titulo="Pagamentos", responsavel="Jonathan", ucs="UC06, UC07", modulo="pagamentos"
    )
