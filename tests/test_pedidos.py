"""Fluxos de Pedidos sem depender de credenciais locais."""
from datetime import datetime
from unittest import TestCase, mock
from app import create_app, db
from app.modulos.autenticacao import repo as auth
from app.modulos.clientes import repo as clientes
from app.modulos.pedidos import repo, routes

MODELOS = [{'id': 1, 'modelo': 'Mercosul automovel', 'quantidade': 12}, {'id': 2, 'modelo': 'Mercosul motocicleta', 'quantidade': 4}]
DADOS = dict(cliente_id='1', chassi='9BWZZZ377VT000001', tipo_veiculo='CARRO', posicao='PAR', item_id='1', numero_placa='ABC1D23', qr_dianteira='QR-D', qr_traseira='QR-T', cor_placa='', cor_caracteres='PRETA', observacoes='Teste')
PEDIDO = dict(numero=101, cliente_id=1, cliente_nome='Carla Cliente', documento='11122233344', telefone='34999990001', categoria='PARTICULAR', chassi=DADOS['chassi'], situacao='CRIADO', autorizacao=None, observacoes=None, motivo=None, usuario_nome='Ana', criado_em=datetime(2026, 11, 17), atualizado_em=datetime(2026, 11, 17), placas='Mercosul automovel · par', pagamento=None)

class TestPedidos(TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 't' * 40})
        self.c = self.app.test_client()
        usuario = dict(id=2, nome='Funcionário', perfil='FUNCIONARIO', ativo=True)
        self.patches = [mock.patch.object(auth, 'buscar_por_id', return_value=usuario),
            mock.patch.object(clientes, 'buscar', return_value=dict(id=1, nome='Carla', documento='11122233344', categoria='PARTICULAR')),
            mock.patch.object(repo, 'modelos', return_value=MODELOS),
            mock.patch.object(repo, 'buscar', return_value=PEDIDO),
            mock.patch.object(repo, 'listar', return_value=([PEDIDO], 1)),
            mock.patch.object(repo, 'placas', return_value=[]), mock.patch.object(repo, 'pagamento', return_value=None)]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)
        with self.c.session_transaction() as s:
            s['usuario_id'] = 2
            s['_csrf'] = 'teste-csrf'

    def post(self, url, dados):
        return self.c.post(url, data={**dados, 'csrf_token': 'teste-csrf'})

    def test_busca_vazia_nome_e_documento_parcial_nao_consultam_clientes(self):
        with mock.patch.object(repo, 'buscar_cliente_por_documento') as buscar, mock.patch.object(clientes, 'buscar_para_selecao') as listar:
            for url in ('/pedidos/novo', '/pedidos/novo?q=', '/pedidos/novo?q=Carla', '/pedidos/novo?q=111222', '/pedidos/novo?q=abc11122233344'):
                with self.subTest(url=url):
                    r = self.c.get(url)
                    self.assertEqual(r.status_code, 200)
                    self.assertNotIn('Carla', r.get_data(as_text=True).split('id="cliente_id"')[1].split('</select>')[0])
            buscar.assert_not_called()
            listar.assert_not_called()

    def test_busca_documento_completo_com_e_sem_pontuacao(self):
        cliente = dict(id=1, nome='Cliente encontrado', documento='11122233344', categoria='PARTICULAR')
        for termo, documento in [('111.222.333-44', '11122233344'), ('11122233344', '11122233344'), ('11.222.333/0001-99', '11222333000199'), ('11222333000199', '11222333000199')]:
            with self.subTest(termo=termo), mock.patch.object(repo, 'buscar_cliente_por_documento', return_value=cliente) as buscar:
                r = self.c.get('/pedidos/novo', query_string={'q': termo})
                buscar.assert_called_once_with(documento)
                self.assertIn('Cliente encontrado', r.get_data(as_text=True))
        with mock.patch.object(repo, 'buscar_cliente_por_documento', return_value=None):
            r = self.c.get('/pedidos/novo?q=99999999999')
            self.assertIn('Nenhum cliente encontrado', r.get_data(as_text=True))

    def test_telas_e_protecao(self):
        for url in ('/pedidos/', '/pedidos/novo', '/pedidos/101', '/pedidos/101/cancelar'):
            self.assertEqual(self.c.get(url).status_code, 200, url)
        self.assertEqual(self.c.post('/pedidos/101/cancelar', data={'motivo': 'Teste'}).status_code, 400)
        with self.c.session_transaction() as s:
            s.clear()
        for url in ('/pedidos/', '/pedidos/novo', '/pedidos/101', '/pedidos/101/cancelar'):
            self.assertEqual(self.c.get(url).status_code, 302)

    def test_criar_usa_usuario_da_sessao(self):
        with mock.patch.object(repo, 'criar', return_value=101) as criar:
            r = self.post('/pedidos/novo', {**DADOS, 'usuario_id': '999'})
            self.assertEqual(r.status_code, 302)
            self.assertEqual(r.location, '/pedidos/101')
            self.assertEqual(criar.call_args.args[1], 2)

    def test_validacoes_nao_gravam(self):
        for alteracao, mensagem in [({'numero_placa': ''}, '7 caracteres'), ({'qr_traseira': ''}, 'Informe o QR Code'),
                ({'qr_traseira': 'QR-D'}, 'QR Code distinto'), ({'tipo_veiculo': 'MOTO'}, 'apenas a placa traseira'),
                ({'item_id': '2'}, 'apenas a placa traseira'), ({'cor_caracteres': 'BRANCA'}, 'compatível com o fundo')]:
            with self.subTest(alteracao=alteracao), mock.patch.object(repo, 'criar') as criar:
                r = self.post('/pedidos/novo', {**DADOS, **alteracao})
                self.assertEqual(r.status_code, 200)
                self.assertIn(mensagem, r.get_data(as_text=True))
                criar.assert_not_called()

    def test_autorizacao_e_cancelamento(self):
        with mock.patch.object(repo, 'definir_autorizacao') as definir:
            self.assertEqual(self.post('/pedidos/101/autorizacao', {'autorizacao': 'LIBERADA'}).status_code, 302)
            definir.assert_called_once_with(101, 'LIBERADA')
        with mock.patch.object(repo, 'cancelar') as cancelar:
            self.assertEqual(self.post('/pedidos/101/cancelar', {'motivo': '   '}).status_code, 200)
            cancelar.assert_not_called()
            self.assertEqual(self.post('/pedidos/101/cancelar', {'motivo': ' Desistência '}).status_code, 302)
            cancelar.assert_called_once_with(101, 'Desistência')

    def test_erro_do_banco_preserva_formulario(self):
        with mock.patch.object(repo, 'criar', side_effect=Exception('banco')), mock.patch.object(db, 'traduzir_erro', return_value=db.ErroNegocio('QR Code já cadastrado')):
            r = self.post('/pedidos/novo', DADOS)
        texto = r.get_data(as_text=True)
        self.assertIn('QR Code já cadastrado', texto)
        self.assertIn('ABC1D23', texto)
        self.assertIn('value="1" selected', texto)

    def test_filtros_e_paginacao(self):
        with mock.patch.object(repo, 'listar', return_value=([], 31)) as listar:
            self.c.get('/pedidos/?situacao=CRIADO&cliente=Carla&data=2026-11-17&chassi=9BW&page=2')
            listar.assert_called_once_with(dict(situacao='CRIADO', cliente='Carla', data='2026-11-17', chassi='9BW'), 15, 15)
        with mock.patch.object(repo, 'buscar', return_value=None):
            self.assertEqual(self.c.get('/pedidos/999').status_code, 404)

class TestTransacaoPedido(TestCase):
    def test_par_commita_uma_vez_e_erro_da_segunda_placa_desfaz_tudo(self):
        dados, erros = routes.validar(DADOS, MODELOS)
        self.assertFalse(erros)
        for falha in (False, True):
            with self.subTest(falha=falha):
                conn = mock.MagicMock()
                cur = conn.cursor.return_value.__enter__.return_value
                cur.fetchone.side_effect = [{'id': 1}, {'p_numero': 101}]
                if falha:
                    cur.execute.side_effect = [None, None, None, ValueError('QR duplicado')]
                with mock.patch.object(db, 'get_conn', return_value=conn):
                    if falha:
                        with self.assertRaises(ValueError):
                            repo.criar(dados, 2)
                        conn.commit.assert_not_called()
                        conn.rollback.assert_called_once()
                    else:
                        self.assertEqual(repo.criar(dados, 2), 101)
                        conn.commit.assert_called_once()
                        conn.rollback.assert_not_called()
                chamadas = cur.execute.call_args_list
                self.assertTrue(chamadas[1].args[0].startswith('CALL public.sp_criar_pedido'))
                self.assertEqual(chamadas[2].args[1][2], 'DIANTEIRA')
                self.assertEqual(chamadas[3].args[1][2], 'TRASEIRA')
