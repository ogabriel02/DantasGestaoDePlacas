"""Menu lateral. Para incluir uma area nova, acrescente o item aqui (so o Gabriel altera).

Convencao: cada modulo expoe um blueprint cujo nome e o campo "bp" e uma rota "index".
"""
from flask import request, url_for
from werkzeug.routing import BuildError

_SVG = {
    "painel": '<rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/>',
    "pedidos": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>',
    "clientes": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "pagamentos": '<rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
    "estoque": '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    "relatorios": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "usuarios": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
}

GRUPOS = [
    {"titulo": "Operação", "perfis": None, "itens": [
        {"bp": "painel", "rotulo": "Painel"},
        {"bp": "pedidos", "rotulo": "Pedidos"},
        {"bp": "clientes", "rotulo": "Clientes e despachantes"},
        {"bp": "pagamentos", "rotulo": "Pagamentos"},
    ]},
    {"titulo": "Administração", "perfis": ("ADMINISTRADOR",), "itens": [
        {"bp": "estoque", "rotulo": "Estoque"},
        {"bp": "relatorios", "rotulo": "Relatórios"},
        {"bp": "usuarios", "rotulo": "Usuários"},
    ]},
]


def _url(bp):
    try:
        return url_for(f"{bp}.index")
    except BuildError:
        return "#"


def montar_menu(perfil):
    atual = request.blueprint
    menu = []
    for grupo in GRUPOS:
        if grupo["perfis"] and perfil not in grupo["perfis"]:
            continue
        itens = [
            {"rotulo": i["rotulo"], "url": _url(i["bp"]), "icone": _SVG[i["bp"]], "ativo": atual == i["bp"]}
            for i in grupo["itens"]
        ]
        menu.append({"titulo": grupo["titulo"], "itens": itens})
    return menu


def url_inicial():
    return _url("painel")
