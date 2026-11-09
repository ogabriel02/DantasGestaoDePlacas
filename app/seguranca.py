"""Senhas (PBKDF2), protecao CSRF, controle de acesso e limite de tentativas."""
import base64
import hashlib
import hmac
import secrets
import threading
import time
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, g, redirect, request, session, url_for

ALGORITMO = "pbkdf2_sha256"
ITERACOES = 600_000
ITERACOES_MAX = 5_000_000


# ---------- senhas ----------
def _derivar(senha, salt_bytes, iteracoes):
    bruto = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt_bytes, iteracoes)
    return base64.b64encode(bruto).decode("ascii")


def gerar_hash(senha):
    """Formato: pbkdf2_sha256$iteracoes$salt$hash (o mesmo dos usuarios de exemplo)."""
    salt = secrets.token_hex(16)
    return f"{ALGORITMO}${ITERACOES}${salt}${_derivar(senha, salt.encode('ascii'), ITERACOES)}"


def verificar_senha(senha, armazenado):
    try:
        algoritmo, it, salt, esperado = armazenado.split("$", 3)
        iteracoes = int(it)
    except (ValueError, AttributeError):
        return False
    if algoritmo != ALGORITMO or not 0 < iteracoes <= ITERACOES_MAX:
        return False
    # O salt pode ter sido usado como texto ou como bytes (hex) ao gerar o hash.
    candidatos = [salt.encode("utf-8")]
    try:
        candidatos.append(bytes.fromhex(salt))
    except ValueError:
        pass
    ok = False
    for salt_bytes in candidatos:
        if hmac.compare_digest(_derivar(senha, salt_bytes, iteracoes), esperado):
            ok = True
    return ok


HASH_FALSO = f"{ALGORITMO}$600000${'0' * 32}${base64.b64encode(bytes(32)).decode()}"


# ---------- CSRF ----------
def csrf_token():
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def validar_csrf():
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    enviado = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or ""
    esperado = session.get("_csrf") or ""
    if not esperado or not hmac.compare_digest(enviado.encode("utf-8"), esperado.encode("utf-8")):
        abort(400)


# ---------- acesso ----------
def destino_seguro(destino):
    """Aceita apenas caminhos internos (evita redirecionamento para outro site)."""
    if not destino or not destino.startswith("/") or destino.startswith("//") or "\\" in destino:
        return None
    return destino if not urlparse(destino).netloc else None


def carregar_usuario():
    """Antes de cada requisicao: confere se o usuario da sessao ainda existe e esta ativo."""
    g.usuario = None
    if request.endpoint == "static":
        return
    usuario_id = session.get("usuario_id")
    if usuario_id:
        from app.modulos.autenticacao import repo

        usuario = repo.buscar_por_id(usuario_id)
        if usuario and usuario["ativo"]:
            g.usuario = usuario
        else:
            session.clear()


def _destino_atual():
    if request.method != "GET":
        return None
    return request.path + ("?" + request.query_string.decode() if request.query_string else "")


def login_required(view):
    @wraps(view)
    def interna(*args, **kwargs):
        if g.get("usuario") is None:
            flash("Faça login para continuar.", "info")
            return redirect(url_for("autenticacao.login", next=_destino_atual()))
        return view(*args, **kwargs)

    return interna


def perfil_required(*perfis):
    def decorador(view):
        @wraps(view)
        @login_required
        def interna(*args, **kwargs):
            if g.usuario["perfil"] not in perfis:
                abort(403)
            return view(*args, **kwargs)

        return interna

    return decorador


# ---------- limite de tentativas de login ----------
_LIMITE, _JANELA, _BLOQUEIO = 5, 900, 300
_falhas = {}
_trava = threading.Lock()


def segundos_bloqueado(chave):
    with _trava:
        registro = _falhas.get(chave)
        agora = time.time()
        if registro and registro["ate"] > agora:
            return int(registro["ate"] - agora) + 1
        return 0


def registrar_falha(chave):
    agora = time.time()
    with _trava:
        registro = _falhas.get(chave)
        if not registro or agora - registro["inicio"] > _JANELA or (registro["ate"] and registro["ate"] < agora):
            registro = {"n": 0, "inicio": agora, "ate": 0}
            _falhas[chave] = registro
        registro["n"] += 1
        if registro["n"] >= _LIMITE:
            registro["ate"] = agora + _BLOQUEIO


def limpar_falhas(chave):
    with _trava:
        _falhas.pop(chave, None)
