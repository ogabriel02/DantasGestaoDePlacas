"""UC04, UC05, UC08 e UC09 — pedidos (Tatiane)."""
from datetime import date
import re
from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from app import db
from app.seguranca import login_required
from app.modulos.clientes import repo as clientes_repo
from . import repo

bp = Blueprint('pedidos', __name__, url_prefix='/pedidos', template_folder='templates', static_folder='static')
SITUACOES = {'CRIADO': 'Criado', 'AGUARDANDO_PAGAMENTO': 'Aguardando pagamento', 'EM_PRODUCAO': 'Em produção', 'FINALIZADO': 'Finalizado', 'CANCELADO': 'Cancelado'}
AUTORIZACOES = {'': 'Não iniciada', 'NAO_SOLICITADA': 'Não solicitada', 'PENDENTE': 'Aguardando autorização', 'LIBERADA': 'Liberada', 'NEGADA': 'Negada'}

@bp.context_processor
def contexto():
    return dict(situacoes=SITUACOES, autorizacoes=AUTORIZACOES)

def erro_banco(exc):
    restricao = getattr(getattr(exc, 'diag', None), 'constraint_name', None)
    mensagens = {'uk_placa_qr': 'Este QR Code já está cadastrado em outra placa.',
                 'ck_placa_cores': 'A combinação de fundo e caracteres não é permitida.',
                 'ck_placa_numero': 'O número da placa deve ter 7 caracteres.',
                 'fk_pedido_cliente': 'O cliente selecionado não existe.',
                 'fk_placa_item': 'O modelo selecionado não existe.'}
    if restricao in mensagens:
        flash(mensagens[restricao], 'erro')
    elif (erro := db.traduzir_erro(exc)):
        flash(erro.mensagem, 'erro')
    else:
        raise exc

@bp.route('/')
@login_required
def index():
    filtros = {k: request.args.get(k, '').strip() for k in ('situacao', 'cliente', 'data', 'chassi')}
    if filtros['situacao'] not in SITUACOES:
        filtros['situacao'] = ''
    if filtros['data']:
        try:
            date.fromisoformat(filtros['data'])
        except ValueError:
            flash('Informe uma data válida.', 'erro')
            filtros['data'] = ''
    pagina = max(1, request.args.get('page', 1, type=int))
    pedidos, total = repo.listar(filtros, 15, (pagina - 1) * 15)
    paginas = max(1, (total + 14) // 15)
    if pagina > paginas:
        return redirect(url_for('pedidos.index', page=paginas, **filtros))
    return render_template('pedidos/lista.html', pedidos=pedidos, total=total, pagina=pagina, paginas=paginas, filtros=filtros)

def validar(form, modelos):
    dados = {k: form.get(k, '').strip() for k in ('cliente_id', 'chassi', 'tipo_veiculo', 'posicao', 'item_id', 'numero_placa', 'qr_dianteira', 'qr_traseira', 'cor_placa', 'cor_caracteres', 'observacoes')}
    dados['chassi'] = dados['chassi'].upper()
    dados['numero_placa'] = dados['numero_placa'].upper()
    erros = {}
    for chave in ('cliente_id', 'item_id'):
        try:
            dados[chave] = int(dados[chave])
            if dados[chave] < 1:
                raise ValueError
        except ValueError:
            erros[chave] = 'Selecione uma opção válida.'
    if len(dados['chassi']) != 17:
        erros['chassi'] = 'Informe os 17 caracteres do chassi.'
    if dados['tipo_veiculo'] not in ('CARRO', 'MOTO'):
        erros['tipo_veiculo'] = 'Selecione o tipo de veículo.'
    if dados['posicao'] not in ('DIANTEIRA', 'TRASEIRA', 'PAR'):
        erros['posicao'] = 'Selecione dianteira, traseira ou par.'
    modelo = next((m for m in modelos if m['id'] == dados['item_id']), None)
    if not modelo:
        erros['item_id'] = 'Selecione um modelo disponível no cadastro.'
    moto = dados['tipo_veiculo'] == 'MOTO' or (modelo and 'moto' in modelo['modelo'].lower())
    if moto and dados['posicao'] != 'TRASEIRA':
        erros['posicao'] = 'Para moto, apenas a placa traseira é permitida.'
    if modelo:
        nome = modelo['modelo'].lower()
        if ('moto' in nome and dados['tipo_veiculo'] != 'MOTO') or (('automovel' in nome or 'carro' in nome) and dados['tipo_veiculo'] != 'CARRO'):
            erros['item_id'] = 'Escolha um modelo compatível com o veículo.'
    if len(dados['numero_placa']) != 7:
        erros['numero_placa'] = 'Informe os 7 caracteres do número da placa.'
    for posicao in ('DIANTEIRA', 'TRASEIRA'):
        if dados['posicao'] in (posicao, 'PAR'):
            chave = 'qr_' + posicao.lower()
            if not dados[chave] or len(dados[chave]) > 255:
                erros[chave] = 'Informe o QR Code da placa (até 255 caracteres).'
    if dados['posicao'] == 'PAR' and dados['qr_dianteira'] == dados['qr_traseira']:
        erros['qr_traseira'] = 'Cada placa do par precisa de um QR Code distinto.'
    if dados['cor_placa'] not in ('', 'COLECIONADOR'):
        erros['cor_placa'] = 'Escolha um fundo válido.'
    cores = ('BRANCA', 'CINZA_PRATA') if dados['cor_placa'] == 'COLECIONADOR' else ('PRETA', 'VERMELHA', 'AZUL', 'VERDE', 'DOURADA')
    if dados['cor_caracteres'] not in cores:
        erros['cor_caracteres'] = 'Escolha uma cor de caracteres compatível com o fundo.'
    return dados, erros

@bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    busca = request.args.get('q', '').strip()[:80]
    clientes = []
    if request.method == 'GET' and 'q' in request.args:
        documento = re.sub(r'[.\-/\s]', '', busca)
        if not re.fullmatch(r'(?:[0-9]{11}|[0-9]{14})', documento):
            flash('Informe o CPF ou CNPJ completo para buscar o cliente.', 'erro')
        else:
            cliente = repo.buscar_cliente_por_documento(documento)
            if cliente:
                clientes.append(cliente)
            else:
                flash('Nenhum cliente encontrado com este CPF/CNPJ.', 'info')
    modelos = repo.modelos()
    dados = dict(cliente_id='', tipo_veiculo='CARRO', posicao='TRASEIRA', cor_caracteres='PRETA')
    erros = {}
    if request.method == 'POST':
        dados, erros = validar(request.form, modelos)
        if 'cliente_id' not in erros:
            cliente = clientes_repo.buscar(dados['cliente_id'])
            if not cliente:
                erros['cliente_id'] = 'Selecione um cliente existente.'
            elif not any(c['id'] == cliente['id'] for c in clientes):
                clientes.append(cliente)
        if not erros:
            try:
                numero = repo.criar(dados, g.usuario['id'])
            except Exception as exc:
                erro_banco(exc)
            else:
                flash('Pedido registrado com sucesso.', 'ok')
                return redirect(url_for('pedidos.ver', numero=numero))
    return render_template('pedidos/novo.html', dados=dados, erros=erros, clientes=clientes, modelos=modelos, busca=busca)

def buscar_ou_404(numero):
    pedido = repo.buscar(numero)
    if pedido is None:
        abort(404)
    return pedido

@bp.route('/<int:numero>')
@login_required
def ver(numero):
    pedido = buscar_ou_404(numero)
    return render_template('pedidos/detalhe.html', pedido=pedido, placas=repo.placas(numero), pagamento=repo.pagamento(numero))

@bp.route('/<int:numero>/autorizacao', methods=['POST'])
@login_required
def autorizacao(numero):
    buscar_ou_404(numero)
    valor = request.form.get('autorizacao', '')
    if valor not in AUTORIZACOES:
        flash('Escolha uma autorização válida.', 'erro')
    else:
        try:
            repo.definir_autorizacao(numero, valor or None)
        except Exception as exc:
            erro_banco(exc)
        else:
            flash('Autorização externa atualizada.', 'ok')
    return redirect(url_for('pedidos.ver', numero=numero))

@bp.route('/<int:numero>/cancelar', methods=['GET', 'POST'])
@login_required
def cancelar(numero):
    pedido = buscar_ou_404(numero)
    motivo = request.form.get('motivo', '').strip()
    if request.method == 'POST':
        if not motivo:
            flash('Informe o motivo do cancelamento.', 'erro')
        else:
            try:
                repo.cancelar(numero, motivo)
            except Exception as exc:
                erro_banco(exc)
            else:
                flash('Pedido cancelado.', 'ok')
                return redirect(url_for('pedidos.ver', numero=numero))
    return render_template('pedidos/cancelar.html', pedido=pedido, motivo=motivo)
