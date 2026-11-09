"""Relatórios - responsavel: Jonathan (UC11).

Substitua este arquivo pela implementacao real. Mantenha:
  - o blueprint chamado "relatorios" e a rota "index" (o menu lateral usa isso);
  - os templates dentro de app/modulos/relatorios/templates/relatorios/.
Use app.db (todos, um, executar) e as procedures sp_* do banco.
"""
from flask import Blueprint, render_template

from app.seguranca import perfil_required

bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


@bp.route("/")
@perfil_required("ADMINISTRADOR")
def index():
    return render_template(
        "em_construcao.html", titulo="Relatórios", responsavel="Jonathan", ucs="UC11", modulo="relatorios"
    )
