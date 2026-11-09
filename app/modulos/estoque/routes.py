"""Estoque - responsavel: Jonathan (UC10).

Substitua este arquivo pela implementacao real. Mantenha:
  - o blueprint chamado "estoque" e a rota "index" (o menu lateral usa isso);
  - os templates dentro de app/modulos/estoque/templates/estoque/.
Use app.db (todos, um, executar) e as procedures sp_* do banco.
"""
from flask import Blueprint, render_template

from app.seguranca import perfil_required

bp = Blueprint("estoque", __name__, url_prefix="/estoque")


@bp.route("/")
@perfil_required("ADMINISTRADOR")
def index():
    return render_template(
        "em_construcao.html", titulo="Estoque", responsavel="Jonathan", ucs="UC10", modulo="estoque"
    )
