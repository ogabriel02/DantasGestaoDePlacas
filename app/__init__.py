"""Fabrica da aplicacao DGP. Os modulos em app/modulos/* sao registrados automaticamente."""
import importlib
import pkgutil

from flask import Flask, g, render_template
from markupsafe import Markup

from app import db, menu, seguranca, util
from app.config import carregar_config


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(carregar_config())
    if config:
        app.config.update(config)

    chave = app.config.get("SECRET_KEY") or ""
    if len(chave) < 32:
        raise RuntimeError(
            "SECRET_KEY ausente ou curta demais. Preencha no arquivo .env com: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )

    app.teardown_appcontext(db.fechar)
    app.before_request(seguranca.validar_csrf)
    app.before_request(seguranca.carregar_usuario)

    app.jinja_env.globals["csrf_token"] = seguranca.csrf_token
    app.jinja_env.filters["documento"] = util.formatar_documento
    app.jinja_env.filters["telefone"] = util.formatar_telefone
    app.jinja_env.filters["cep"] = util.formatar_cep
    app.jinja_env.filters["perfil_rotulo"] = lambda p: util.PERFIS.get(p, p or "")
    app.jinja_env.filters["data_hora"] = lambda d: d.strftime("%d/%m/%Y %H:%M") if d else ""

    @app.context_processor
    def contexto_global():
        usuario = g.get("usuario")
        return {
            "usuario": usuario,
            "menu": menu.montar_menu(usuario["perfil"]) if usuario else [],
            "home_url": menu.url_inicial(),
            "iniciais": "".join(p[0] for p in usuario["nome"].split()[:2]).upper() if usuario else "",
            "Markup": Markup,
        }

    @app.after_request
    def cabecalhos(resposta):
        resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
        resposta.headers.setdefault("Referrer-Policy", "same-origin")
        if g.get("usuario") is not None:
            resposta.headers["Cache-Control"] = "no-store"
        return resposta

    _registrar_erros(app)
    _registrar_modulos(app)
    return app


def _registrar_modulos(app):
    from app import modulos

    for info in pkgutil.iter_modules(modulos.__path__):
        if not info.ispkg:
            continue
        nome_rotas = f"{modulos.__name__}.{info.name}.routes"
        try:
            rotas = importlib.import_module(nome_rotas)
        except ModuleNotFoundError as exc:
            if exc.name == nome_rotas:  # modulo ainda sem routes.py
                continue
            raise
        blueprint = getattr(rotas, "bp", None)
        if blueprint is not None:
            app.register_blueprint(blueprint)


def _registrar_erros(app):
    def pagina(codigo, titulo, mensagem):
        def tratador(_erro):
            return render_template("erro.html", codigo=codigo, titulo=titulo, mensagem=mensagem), codigo

        return tratador

    app.register_error_handler(400, pagina(400, "Formulário expirado", "A sessão expirou ou o formulário é inválido. Recarregue a página e tente de novo."))
    app.register_error_handler(403, pagina(403, "Acesso negado", "Seu perfil não tem permissão para acessar esta área."))
    app.register_error_handler(404, pagina(404, "Página não encontrada", "O endereço acessado não existe."))
    app.register_error_handler(413, pagina(413, "Dados grandes demais", "O envio excede o tamanho permitido."))
    app.register_error_handler(500, pagina(500, "Erro interno", "Algo inesperado aconteceu. Avise o responsável pelo sistema."))
    app.register_error_handler(db.OperationalError, pagina(503, "Banco de dados indisponível", "Não foi possível conectar ao PostgreSQL. Confira se o serviço está ligado e se os dados do arquivo .env estão corretos."))
