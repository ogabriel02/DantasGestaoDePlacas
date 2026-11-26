"""UC11 Emitir relatorios (Jonathan). Somente administrador. Somente leitura.

Visoes: resumo por situacao, por despachante, por tipo de placa e lista de pedidos.
Filtros: periodo, despachante, tipo de placa e situacao. Exportacao em CSV (Excel).
"""
import csv
import io
from datetime import date
from decimal import Decimal

from flask import Blueprint, Response, flash, render_template, request

from app import util
from app.modulos.pagamentos import comum
from app.seguranca import perfil_required
from . import repo

bp = Blueprint("relatorios", __name__, url_prefix="/relatorios", template_folder="templates", static_folder="static")

VISOES = {"resumo": "Resumo do período", "despachantes": "Por despachante", "tipos": "Por tipo de placa", "pedidos": "Lista de pedidos"}
LIMITE_TELA = 200
LIMITE_CSV = 20_000


def _id(texto, validos):
    texto = (texto or "").strip()
    return int(texto) if texto.isdigit() and int(texto) in validos else None


def ler_filtros(args, despachantes, modelos):
    """Valida os filtros da URL. Retorna (filtros, erros); filtro invalido volta ao padrao."""
    hoje = date.today()
    erros = []
    datas = {}
    for campo, padrao in (("inicio", hoje.replace(day=1)), ("fim", hoje)):
        texto = (args.get(campo) or "").strip()
        try:
            datas[campo] = date.fromisoformat(texto) if texto else padrao
        except ValueError:
            erros.append(f"Data {'inicial' if campo == 'inicio' else 'final'} inválida.")
            datas[campo] = padrao
    if datas["inicio"] > datas["fim"]:
        erros.append("A data inicial não pode ser depois da data final.")
        datas["inicio"], datas["fim"] = datas["fim"], datas["inicio"]
    filtros = {
        "inicio": datas["inicio"], "fim": datas["fim"],
        "despachante": _id(args.get("despachante"), {d["id"] for d in despachantes}),
        "item": _id(args.get("item"), {m["id"] for m in modelos}),
        "situacao": args.get("situacao") if args.get("situacao") in comum.SITUACOES else "",
    }
    if args.get("despachante") and filtros["despachante"] is None:
        erros.append("Despachante inválido; o filtro foi ignorado.")
    if args.get("item") and filtros["item"] is None:
        erros.append("Tipo de placa inválido; o filtro foi ignorado.")
    return filtros, erros


def _totais(linhas, campos):
    return {c: sum((l[c] for l in linhas), Decimal(0) if c in ("cobrado", "recebido") else 0) for c in campos}


def _dados(visao, filtros, limite):
    if visao == "despachantes":
        linhas = repo.por_despachante(filtros)
        return linhas, _totais(linhas, ("pedidos", "placas", "finalizados", "cancelados", "em_aberto", "cobrado", "recebido"))
    if visao == "tipos":
        linhas = repo.por_tipo_placa(filtros)
        return linhas, _totais(linhas, ("placas", "pedidos", "dianteiras", "traseiras", "entregues", "canceladas"))
    if visao == "pedidos":
        linhas = repo.pedidos(filtros, limite)
        return linhas, {"pedidos": len(linhas)}
    por_situacao = {l["situacao"]: l for l in repo.resumo(filtros)}
    linhas = [{"situacao": s, "rotulo": r, **{k: por_situacao.get(s, {}).get(k, 0) for k in ("pedidos", "placas", "cobrado", "recebido")}}
              for s, r in comum.SITUACOES.items()]
    return linhas, _totais(linhas, ("pedidos", "placas", "cobrado", "recebido"))


def _args_url(filtros, visao):
    args = {"visao": visao, "inicio": filtros["inicio"].isoformat(), "fim": filtros["fim"].isoformat()}
    for chave in ("despachante", "item", "situacao"):
        if filtros[chave]:
            args[chave] = filtros[chave]
    return args


def _contexto_filtros():
    despachantes, modelos = repo.despachantes(), repo.modelos()
    filtros, erros = ler_filtros(request.args, despachantes, modelos)
    visao = request.args.get("visao") if request.args.get("visao") in VISOES else "resumo"
    return despachantes, modelos, filtros, erros, visao


@bp.route("/")
@perfil_required("ADMINISTRADOR")
def index():
    despachantes, modelos, filtros, erros, visao = _contexto_filtros()
    for erro in erros:
        flash(erro, "erro")
    linhas, totais = _dados(visao, filtros, LIMITE_TELA + 1)
    excedeu = visao == "pedidos" and len(linhas) > LIMITE_TELA
    if excedeu:
        linhas = linhas[:LIMITE_TELA]
        totais = {"pedidos": LIMITE_TELA}
    return render_template(
        "relatorios/index.html", visoes=VISOES, visao=visao, filtros=filtros, linhas=linhas, totais=totais,
        despachantes=despachantes, modelos=modelos, situacoes=comum.SITUACOES, selo_situacao=comum.SELO_SITUACAO,
        pagamentos_rotulo=comum.PAGAMENTOS, args_url=_args_url(filtros, visao), excedeu=excedeu, limite_tela=LIMITE_TELA,
        geral=_dados("resumo", filtros, 0)[1] if visao != "resumo" else totais,
    )


# ---------- CSV ----------
def _celula(valor):
    """Formata para o Excel em portugues e neutraliza formulas (injecao de CSV)."""
    if valor is None:
        return ""
    if isinstance(valor, Decimal):
        return f"{valor:.2f}".replace(".", ",")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y %H:%M") if hasattr(valor, "hour") else valor.strftime("%d/%m/%Y")
    texto = str(valor)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


def _colunas(visao):
    if visao == "despachantes":
        return [("Despachante", lambda l: l["nome"]), ("CNPJ/CPF", lambda l: util.formatar_documento(l["documento"])),
                ("Pedidos", "pedidos"), ("Placas", "placas"), ("Finalizados", "finalizados"), ("Em aberto", "em_aberto"),
                ("Cancelados", "cancelados"), ("Valor cobrado (R$)", "cobrado"), ("Valor recebido (R$)", "recebido")]
    if visao == "tipos":
        return [("Tipo de placa", "modelo"), ("Placas", "placas"), ("Pedidos", "pedidos"), ("Dianteiras", "dianteiras"),
                ("Traseiras", "traseiras"), ("Entregues (finalizadas)", "entregues"), ("Em pedidos cancelados", "canceladas")]
    if visao == "pedidos":
        return [("Pedido", "numero"), ("Data", "criado_em"), ("Cliente", "cliente_nome"),
                ("Categoria", lambda l: "Despachante" if l["categoria"] == "DESPACHANTE" else "Particular"),
                ("CPF/CNPJ", lambda l: util.formatar_documento(l["documento"])),
                ("Situação", lambda l: comum.SITUACOES.get(l["situacao"], l["situacao"])), ("Placas", "placas"),
                ("Tipos de placa", "descricao_placas"), ("Valor (R$)", "valor"),
                ("Pagamento", lambda l: comum.PAGAMENTOS.get(l["pagamento_situacao"], "Sem cobrança")),
                ("Confirmado em", "data_confirmacao")]
    return [("Situação", "rotulo"), ("Pedidos", "pedidos"), ("Placas", "placas"),
            ("Valor cobrado (R$)", "cobrado"), ("Valor recebido (R$)", "recebido")]


@bp.route("/exportar.csv")
@perfil_required("ADMINISTRADOR")
def exportar():
    _despachantes, _modelos, filtros, _erros, visao = _contexto_filtros()
    linhas, totais = _dados(visao, filtros, LIMITE_CSV)
    colunas = _colunas(visao)
    saida = io.StringIO()
    escritor = csv.writer(saida, delimiter=";", lineterminator="\r\n")
    escritor.writerow([f"Relatório DGP - {VISOES[visao]}",
                       f"Período: {filtros['inicio']:%d/%m/%Y} a {filtros['fim']:%d/%m/%Y}"])
    escritor.writerow([titulo for titulo, _ in colunas])
    for linha in linhas:
        escritor.writerow([_celula(campo(linha) if callable(campo) else linha.get(campo)) for _, campo in colunas])
    if visao != "pedidos":
        escritor.writerow([_celula(totais.get(campo)) if not callable(campo) and campo in totais else ("Total" if i == 0 else "")
                           for i, (_, campo) in enumerate(colunas)])
    nome = f"relatorio_{visao}_{filtros['inicio']:%Y%m%d}_{filtros['fim']:%Y%m%d}.csv"
    return Response(
        "﻿" + saida.getvalue(), content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
