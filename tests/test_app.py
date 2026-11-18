"""Testes de rotas com repositorios simulados (nao precisam do PostgreSQL)."""
import unittest
from types import SimpleNamespace
from unittest import mock

from app import create_app, db, seguranca
from app.modulos.autenticacao import repo as repo_auth
from app.modulos.clientes import repo as repo_cli
from app.modulos.usuarios import repo as repo_usu


class ErroPG(Exception):
    def __init__(self, constraint=None, mensagem=None):
        super().__init__("erro")
        self.diag = SimpleNamespace(constraint_name=constraint, message_primary=mensagem)


class Unico(ErroPG): ...
class Check(ErroPG): ...
class Levantada(ErroPG): ...


FAKE_PG = SimpleNamespace(UniqueViolation=Unico, CheckViolation=Check, RaiseException=Levantada,
                          StringDataRightTruncation=type("T", (ErroPG,), {}),
                          InsufficientPrivilege=type("P", (ErroPG,), {}))

CLIENTE_OK = {
    "tipo_pessoa": "PF", "categoria": "PARTICULAR", "documento": "529.982.247-25", "nome": "Carla Cliente",
    "cep": "38400-000", "rua": "Rua Exemplo", "numero": "100", "bairro": "Centro", "cidade": "Uberlandia",
    "uf": "MG", "complemento": "", "telefone": "(34) 99999-0001", "email": "carla@example.invalid",
}


class Base(unittest.TestCase):
    def setUp(self):
        self._it = seguranca.ITERACOES
        seguranca.ITERACOES = 1000
        seguranca._falhas.clear()
        senha = seguranca.gerar_hash("Senha@1234")
        self.usuarios = {
            1: {"id": 1, "nome": "Ana Exemplo", "login": "ana.admin", "senha_hash": senha, "perfil": "ADMINISTRADOR", "ativo": True},
            2: {"id": 2, "nome": "Bruno Exemplo", "login": "bruno.operador", "senha_hash": senha, "perfil": "FUNCIONARIO", "ativo": True},
            3: {"id": 3, "nome": "Caio Inativo", "login": "caio.inativo", "senha_hash": senha, "perfil": "FUNCIONARIO", "ativo": False},
        }
        self.clientes = {1: {**{k: v for k, v in CLIENTE_OK.items()}, "id": 1, "documento": "11122233344",
                             "cep": "38400000", "telefone": "34999990001", "complemento": None, "pedidos": 0}}
        self.chamadas = []

        def login_de(l):
            return next((u for u in self.usuarios.values() if u["login"] == l), None)

        def criar_usuario(nome, login, h, perfil):
            if login_de(login):
                raise Unico("uk_usuario_login")
            self.usuarios[9] = {"id": 9, "nome": nome, "login": login, "senha_hash": h, "perfil": perfil, "ativo": True}
            self.chamadas.append(("criar_usuario", login, h))
            return 9

        def criar_cliente(d):
            if any(c["documento"] == d["documento"] for c in self.clientes.values()):
                raise Unico("uk_cliente_documento")
            self.clientes[7] = {**d, "id": 7, "pedidos": 0}
            return 7

        def listar_clientes(busca, categoria, limite, desloc):
            linhas = [c for c in self.clientes.values() if busca.lower() in c["nome"].lower()]
            self.chamadas.append(("listar", busca, categoria, limite, desloc))
            return linhas[desloc:desloc + limite], len(linhas)

        self.patches = [
            mock.patch.object(db, "pg_errors", FAKE_PG),
            mock.patch.object(repo_auth, "buscar_por_login", side_effect=login_de),
            mock.patch.object(repo_auth, "buscar_por_id", side_effect=lambda i: self.usuarios.get(i)),
            mock.patch.object(repo_usu, "listar", side_effect=lambda: list(self.usuarios.values())),
            mock.patch.object(repo_usu, "buscar", side_effect=lambda i: self.usuarios.get(i)),
            mock.patch.object(repo_usu, "criar", side_effect=criar_usuario),
            mock.patch.object(repo_usu, "atualizar", side_effect=lambda *a: self.chamadas.append(("atualizar_usuario",) + a)),
            mock.patch.object(repo_usu, "definir_ativo", side_effect=lambda i, a: self.chamadas.append(("ativo", i, a))),
            mock.patch.object(repo_cli, "listar", side_effect=listar_clientes),
            mock.patch.object(repo_cli, "buscar", side_effect=lambda i: self.clientes.get(i)),
            mock.patch.object(repo_cli, "criar", side_effect=criar_cliente),
            mock.patch.object(repo_cli, "atualizar", side_effect=lambda i, d: self.chamadas.append(("atualizar_cliente", i, d))),
        ]
        for p in self.patches:
            p.start()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "k" * 40, "VALIDAR_DIGITO_DOCUMENTO": True})
        self.c = self.app.test_client()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        seguranca.ITERACOES = self._it

    # ajudantes
    def token(self):
        """Pega o token CSRF como o navegador: abre uma pagina que tenha formulario."""
        with self.c.session_transaction() as s:
            token = s.get("_csrf")
        if not token:
            self.c.get("/login")
            with self.c.session_transaction() as s:
                token = s.get("_csrf")
        if not token:  # ja logado: o login redireciona, entao abre o painel
            self.c.get("/")
            with self.c.session_transaction() as s:
                token = s["_csrf"]
        return token

    def post(self, url, dados=None, **kw):
        dados = dict(dados or {})
        dados["csrf_token"] = self.token() if "csrf_token" not in dados else dados["csrf_token"]
        return self.c.post(url, data=dados, **kw)

    def entrar(self, login="ana.admin", senha="Senha@1234"):
        return self.post("/login", {"login": login, "senha": senha})

    @staticmethod
    def texto(resp):
        return resp.get_data(as_text=True)


class TestLogin(Base):
    def test_sem_login_redireciona(self):
        r = self.c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["Location"], "/login?next=/")

    def test_pagina_de_login(self):
        r = self.c.get("/login")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Entrar no sistema", self.texto(r))
        self.assertIn("logo.jpg", self.texto(r))

    def test_post_sem_csrf_e_recusado(self):
        r = self.c.post("/login", data={"login": "ana.admin", "senha": "Senha@1234"})
        self.assertEqual(r.status_code, 400)

    def test_login_correto_e_painel(self):
        r = self.entrar()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["Location"], "/")
        painel = self.c.get("/")
        self.assertEqual(painel.status_code, 200)
        t = self.texto(painel)
        for item in ("Painel", "Pedidos", "Clientes e despachantes", "Pagamentos", "Estoque", "Relatórios", "Usuários"):
            self.assertIn(item, t)
        self.assertIn("Dantas Gestão de Placas", t)
        self.assertEqual(painel.headers["Cache-Control"], "no-store")
        self.assertEqual(painel.headers["X-Frame-Options"], "DENY")

    def test_funcionario_nao_ve_area_admin(self):
        self.entrar("bruno.operador")
        t = self.texto(self.c.get("/"))
        self.assertNotIn("Administração", t)
        self.assertNotIn(">Usuários<", t)

    def test_credenciais_invalidas_e_inativo(self):
        for login, senha in (("ana.admin", "errada"), ("naoexiste", "Senha@1234"), ("caio.inativo", "Senha@1234")):
            r = self.entrar(login, senha)
            self.assertEqual(r.status_code, 200)
            self.assertIn("Login ou senha inválidos, ou usuário inativo.", self.texto(r))
        self.assertEqual(self.c.get("/").status_code, 302)

    def test_login_ignora_maiusculas(self):
        self.assertEqual(self.entrar("ANA.ADMIN").status_code, 302)

    def test_next_seguro(self):
        r = self.post("/login", {"login": "ana.admin", "senha": "Senha@1234", "next": "/clientes"})
        self.assertEqual(r.headers["Location"], "/clientes")
        self.c.post("/logout", data={"csrf_token": self.token()})
        for ruim in ("//evil.com", "https://evil.com"):
            r = self.post("/login", {"login": "ana.admin", "senha": "Senha@1234", "next": ruim})
            self.assertEqual(r.headers["Location"], "/")
            self.c.post("/logout", data={"csrf_token": self.token()})

    def test_bloqueio_apos_varias_falhas(self):
        for _ in range(5):
            self.entrar("ana.admin", "errada")
        r = self.entrar("ana.admin", "Senha@1234")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Muitas tentativas", self.texto(r))

    def test_logout(self):
        self.entrar()
        r = self.post("/logout")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.c.get("/").status_code, 302)
        self.assertEqual(self.c.get("/logout").status_code, 405)

    def test_usuario_inativado_durante_a_sessao_e_expulso(self):
        self.entrar("bruno.operador")
        self.assertEqual(self.c.get("/").status_code, 200)
        self.usuarios[2]["ativo"] = False
        self.assertEqual(self.c.get("/").status_code, 302)


class TestUsuarios(Base):
    def test_somente_administrador(self):
        self.entrar("bruno.operador")
        for url in ("/usuarios/", "/usuarios/novo", "/estoque/", "/relatorios/"):
            self.assertEqual(self.c.get(url).status_code, 403, url)

    def test_lista_e_formularios(self):
        self.entrar()
        t = self.texto(self.c.get("/usuarios/"))
        for nome in ("Ana Exemplo", "Bruno Exemplo", "Caio Inativo"):
            self.assertIn(nome, t)
        self.assertEqual(self.c.get("/usuarios/novo").status_code, 200)
        self.assertEqual(self.c.get("/usuarios/2/editar").status_code, 200)
        self.assertEqual(self.c.get("/usuarios/99/editar").status_code, 404)

    def test_cadastro_valido_grava_com_hash(self):
        self.entrar()
        r = self.post("/usuarios/novo", {"nome": "Novo Usuário", "login": "Novo.User", "perfil": "FUNCIONARIO",
                                          "senha": "SenhaNova1", "confirmar": "SenhaNova1"})
        self.assertEqual(r.status_code, 302)
        _, login, h = self.chamadas[-1]
        self.assertEqual(login, "novo.user")
        self.assertNotIn("SenhaNova1", h)
        self.assertTrue(seguranca.verificar_senha("SenhaNova1", h))

    def test_validacoes(self):
        self.entrar()
        r = self.post("/usuarios/novo", {"nome": "A", "login": "x y", "perfil": "ROOT", "senha": "123", "confirmar": "456"})
        t = self.texto(r)
        self.assertEqual(r.status_code, 200)
        for msg in ("Informe o nome", "Use 3 a 60 caracteres", "Escolha um perfil", "A senha deve ter de 8 a 128"):
            self.assertIn(msg, t)
        self.assertFalse(self.chamadas)

    def test_confirmacao_diferente(self):
        self.entrar()
        t = self.texto(self.post("/usuarios/novo", {"nome": "Fulano", "login": "fulano", "perfil": "FUNCIONARIO",
                                                    "senha": "SenhaNova1", "confirmar": "SenhaNova2"}))
        self.assertIn("não confere", t)

    def test_login_duplicado(self):
        self.entrar()
        r = self.post("/usuarios/novo", {"nome": "Outro Bruno", "login": "bruno.operador", "perfil": "FUNCIONARIO",
                                          "senha": "SenhaNova1", "confirmar": "SenhaNova1"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Este login já existe", self.texto(r))

    def test_editar_sem_trocar_senha(self):
        self.entrar()
        r = self.post("/usuarios/2/editar", {"nome": "Bruno Novo", "login": "bruno.operador", "perfil": "FUNCIONARIO"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.chamadas[-1], ("atualizar_usuario", 2, "Bruno Novo", "bruno.operador", "FUNCIONARIO", None))

    def test_ninguem_altera_o_proprio_perfil(self):
        self.entrar()
        self.post("/usuarios/1/editar", {"nome": "Ana Exemplo", "login": "ana.admin", "perfil": "FUNCIONARIO"})
        self.assertEqual(self.chamadas[-1][4], "ADMINISTRADOR")

    def test_inativar_e_reativar(self):
        self.entrar()
        self.assertEqual(self.post("/usuarios/2/status").status_code, 302)
        self.assertEqual(self.chamadas[-1], ("ativo", 2, False))
        self.post("/usuarios/3/status")
        self.assertEqual(self.chamadas[-1], ("ativo", 3, True))

    def test_nao_inativa_a_si_mesmo(self):
        self.entrar()
        r = self.post("/usuarios/1/status", follow_redirects=True)
        self.assertIn("não pode inativar a sua própria conta", self.texto(r))
        self.assertFalse([c for c in self.chamadas if c[0] == "ativo"])


class TestClientes(Base):
    def test_lista_busca_e_pagina(self):
        self.entrar("bruno.operador")
        r = self.c.get("/clientes/?q=carla")
        t = self.texto(r)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Carla Cliente", t)
        self.assertIn("111.222.333-44", t)
        self.assertIn("(34) 99999-0001", t)
        self.assertIn(("listar", "carla", "", 15, 0), self.chamadas)
        self.assertEqual(self.c.get("/clientes/?page=99").status_code, 302)
        self.assertEqual(self.c.get("/clientes/?categoria=HACK").status_code, 200)

    def test_item_do_menu_fica_ativo(self):
        self.entrar()
        t = self.texto(self.c.get("/clientes/"))
        self.assertRegex(t, r'(?s)menu-item ativo"[^>]*aria-current="page">\s*<span class="menu-icone">.*?Clientes e despachantes', )

    def test_formulario_novo_traz_estados(self):
        self.entrar()
        t = self.texto(self.c.get("/clientes/novo"))
        self.assertIn('<option value="MG" selected>MG</option>', t)
        self.assertIn('<option value="SP">SP</option>', t)

    def test_cadastro_valido_normaliza_dados(self):
        self.entrar()
        r = self.post("/clientes/novo", CLIENTE_OK)
        self.assertEqual(r.status_code, 302)
        salvo = self.clientes[7]
        self.assertEqual(salvo["documento"], "52998224725")
        self.assertEqual(salvo["cep"], "38400000")
        self.assertEqual(salvo["telefone"], "34999990001")
        self.assertIsNone(salvo["complemento"])

    def test_cadastro_invalido(self):
        self.entrar()
        ruim = {**CLIENTE_OK, "documento": "111.222.333-44", "cep": "123", "telefone": "99", "email": "x", "uf": "ZZ", "nome": "Jo"}
        r = self.post("/clientes/novo", ruim)
        t = self.texto(r)
        self.assertEqual(r.status_code, 200)
        for msg in ("CPF inválido", "O CEP deve ter 8 dígitos", "Informe o telefone com DDD", "e-mail válido", "Escolha o estado", "Informe o nome"):
            self.assertIn(msg, t)
        self.assertNotIn(7, self.clientes)

    def test_documento_com_tamanho_errado_para_o_tipo(self):
        self.entrar()
        t = self.texto(self.post("/clientes/novo", {**CLIENTE_OK, "tipo_pessoa": "PJ"}))
        self.assertIn("O CNPJ deve ter 14 dígitos", t)

    def test_validacao_de_digito_pode_ser_desligada(self):
        self.app.config["VALIDAR_DIGITO_DOCUMENTO"] = False
        self.entrar()
        r = self.post("/clientes/novo", {**CLIENTE_OK, "documento": "11122233355"})
        self.assertEqual(r.status_code, 302)

    def test_documento_duplicado(self):
        self.entrar()
        self.app.config["VALIDAR_DIGITO_DOCUMENTO"] = False
        r = self.post("/clientes/novo", {**CLIENTE_OK, "documento": "11122233344"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Já existe um cadastro com este documento", self.texto(r))

    def test_detalhe_e_404(self):
        self.entrar()
        self.assertIn("Carla Cliente", self.texto(self.c.get("/clientes/1")))
        self.assertEqual(self.c.get("/clientes/99").status_code, 404)
        self.assertEqual(self.c.get("/clientes/99/editar").status_code, 404)

    def test_editar_mantem_documento_antigo_mesmo_sem_digito_valido(self):
        self.entrar()
        dados = {**CLIENTE_OK, "documento": "111.222.333-44", "nome": "Carla Renomeada"}
        r = self.post("/clientes/1/editar", dados)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.chamadas[-1][2]["nome"], "Carla Renomeada")

    def test_editar_documento_novo_exige_digito_valido(self):
        self.entrar()
        r = self.post("/clientes/1/editar", {**CLIENTE_OK, "documento": "111.222.333-55"})
        self.assertIn("CPF inválido", self.texto(r))


class TestGeral(Base):
    def test_pagina_404(self):
        r = self.c.get("/nao-existe")
        self.assertEqual(r.status_code, 404)
        self.assertIn("Página não encontrada", self.texto(r))

    def test_modulos_das_outras_partes_aparecem_como_em_construcao(self):
        self.entrar()
        for url, nome in (("/pagamentos/", "Jonathan"), ("/estoque/", "Jonathan"), ("/relatorios/", "Jonathan")):
            t = self.texto(self.c.get(url))
            self.assertIn(nome, t, url)

    def test_traducao_de_erros_do_banco(self):
        self.assertEqual(db.traduzir_erro(Unico("uk_usuario_login")).campo, "login")
        self.assertEqual(db.traduzir_erro(Check("ck_cliente_documento")).campo, "documento")
        self.assertEqual(db.traduzir_erro(Levantada(mensagem="Estoque insuficiente")).mensagem, "Estoque insuficiente")
        self.assertIsNone(db.traduzir_erro(ValueError("outro")))

    def test_secret_key_curta_impede_inicio(self):
        with self.assertRaises(RuntimeError):
            create_app({"SECRET_KEY": "curta"})

    def test_banco_fora_do_ar_mostra_pagina_503(self):
        with mock.patch.object(repo_auth, "buscar_por_id", side_effect=db.OperationalError("sem conexao")):
            self.entrar()
            with self.c.session_transaction() as s:
                s["usuario_id"] = 1
            r = self.c.get("/")
        self.assertEqual(r.status_code, 503)
        self.assertIn("Banco de dados indisponível", self.texto(r))


if __name__ == "__main__":
    unittest.main()
