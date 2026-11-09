"""Painel - responsavel: Jonathan (UC12).

Substitua este arquivo pela implementacao real. Mantenha:
  - o blueprint chamado "painel" e a rota "index" (o menu lateral usa isso);
  - os templates dentro de app/modulos/painel/templates/painel/.
Use app.db (todos, um, executar) e as procedures sp_* do banco.
"""
from flask import Blueprint, render_template

from app.seguranca import login_required

bp = Blueprint("painel", __name__, url_prefix="")


@bp.route("/")
@login_required
def index():
    return render_template(
        "em_construcao.html", titulo="Painel", responsavel="Jonathan", ucs="UC12", modulo="painel"
    )
