"""Acesso ao PostgreSQL (psycopg 3). Uma conexao por requisicao.

Regra do projeto: pedidos, placas, pagamentos e estoque so sao gravados
pelas procedures do banco (CALL public.sp_...). Use `executar` para isso.
"""
from flask import current_app, g

try:
    import psycopg
    from psycopg import errors as pg_errors
    from psycopg.rows import dict_row

    OperationalError = psycopg.OperationalError
except ImportError:  # permite importar o projeto sem o driver (ex.: testes)
    psycopg = None
    pg_errors = None
    dict_row = None

    class OperationalError(Exception):
        pass


class ErroNegocio(Exception):
    """Erro do banco traduzido para uma mensagem amigavel."""

    def __init__(self, mensagem, campo=None):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.campo = campo


_UNICOS = {
    "uk_usuario_login": ("login", "Este login já existe. Informe outro."),
    "uk_cliente_documento": ("documento", "Já existe um cadastro com este documento."),
}
_CHECKS = {
    "ck_usuario_perfil": ("perfil", "Perfil inválido."),
    "ck_cliente_documento": ("documento", "Documento inválido para o tipo de pessoa."),
    "ck_cliente_tipo": ("tipo_pessoa", "Tipo de pessoa inválido."),
    "ck_cliente_categoria": ("categoria", "Categoria inválida."),
}


def get_conn():
    conn = g.get("_db")
    if conn is None:
        if psycopg is None:
            raise RuntimeError("Biblioteca psycopg não instalada. Rode: pip install -r requirements.txt")
        cfg = current_app.config
        conn = psycopg.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            dbname=cfg["DB_NAME"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            connect_timeout=5,
            row_factory=dict_row,
        )
        g._db = conn
    return conn


def fechar(_exc=None):
    conn = g.pop("_db", None)
    if conn is not None:
        try:
            conn.rollback()
        finally:
            conn.close()


def todos(sql, params=()):
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def um(sql, params=()):
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def executar(sql, params=(), retornar=False):
    """Executa INSERT/UPDATE/CALL e confirma. Com retornar=True devolve a linha."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            linha = cur.fetchone() if retornar else None
        conn.commit()
        return linha
    except Exception:
        conn.rollback()
        raise


def traduzir_erro(exc):
    """Converte erros conhecidos do banco em ErroNegocio. Desconhecido -> None."""
    if pg_errors is None:
        return None
    constraint = getattr(getattr(exc, "diag", None), "constraint_name", None)
    if isinstance(exc, pg_errors.UniqueViolation):
        campo, msg = _UNICOS.get(constraint, (None, "Já existe um registro com estes dados."))
        return ErroNegocio(msg, campo)
    if isinstance(exc, pg_errors.CheckViolation):
        campo, msg = _CHECKS.get(constraint, (None, "Algum dado informado não é válido."))
        return ErroNegocio(msg, campo)
    if isinstance(exc, pg_errors.RaiseException):
        return ErroNegocio(exc.diag.message_primary or "Operação recusada pelo banco.")
    if isinstance(exc, pg_errors.StringDataRightTruncation):
        return ErroNegocio("Algum campo excede o tamanho permitido.")
    if isinstance(exc, pg_errors.InsufficientPrivilege):
        return ErroNegocio("O acesso da aplicação não tem permissão para esta operação. Fale com o responsável pelo banco.")
    return None
