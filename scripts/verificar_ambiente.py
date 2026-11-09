"""Confere se o computador esta pronto para rodar o DGP.

Uso (com o ambiente virtual ativo):  python scripts/verificar_ambiente.py
"""
import re
import sys
from importlib import metadata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

falhas = []


def ok(msg):
    print(f"[ OK  ] {msg}")


def aviso(msg):
    print(f"[AVISO] {msg}")


def falha(msg):
    print(f"[FALHA] {msg}")
    falhas.append(msg)


def verificar_python():
    atual = sys.version_info
    if (atual.major, atual.minor) == (3, 13):
        ok(f"Python {atual.major}.{atual.minor}.{atual.micro}")
    else:
        falha(f"Python {atual.major}.{atual.minor}.{atual.micro} encontrado; o padrão do grupo é 3.13.x")


def verificar_pacotes():
    for linha in (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "==" not in linha:
            continue
        nome, versao = linha.split("==", 1)
        nome = re.sub(r"\[.*\]", "", nome)
        try:
            instalada = metadata.version(nome)
        except metadata.PackageNotFoundError:
            falha(f"{nome} não instalado. Rode: pip install -r requirements.txt")
            continue
        if instalada == versao:
            ok(f"{nome} {instalada}")
        else:
            falha(f"{nome} {instalada} instalado, mas o projeto usa {versao}. Rode: pip install -r requirements.txt")


def verificar_env():
    from app.config import carregar_config

    if not (RAIZ / ".env").exists():
        falha("Arquivo .env não encontrado. Copie .env.example para .env e preencha.")
        return None
    cfg = carregar_config()
    if len(cfg["SECRET_KEY"]) < 32:
        falha("SECRET_KEY ausente ou com menos de 32 caracteres no .env")
    else:
        ok("SECRET_KEY definida")
    if not cfg["DB_PASSWORD"]:
        falha("DB_PASSWORD vazio no .env")
    return cfg


def verificar_banco(cfg):
    import psycopg

    try:
        conn = psycopg.connect(
            host=cfg["DB_HOST"], port=cfg["DB_PORT"], dbname=cfg["DB_NAME"],
            user=cfg["DB_USER"], password=cfg["DB_PASSWORD"], connect_timeout=5,
        )
    except Exception as exc:
        falha(f"Não foi possível conectar ao PostgreSQL: {exc}")
        return
    with conn, conn.cursor() as cur:
        cur.execute("SELECT current_user, version()")
        usuario, versao = cur.fetchone()
        ok(f"Conectado como {usuario}")
        if "PostgreSQL 17" in versao:
            ok(versao.split(",")[0])
        else:
            aviso(f"{versao.split(',')[0]}: o padrão do grupo é PostgreSQL 17.x")

        cur.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
        qtd = cur.fetchone()[0]
        (ok if qtd == 9 else falha)(f"{qtd} tabelas no schema public (esperado: 9)")

        cur.execute("""SELECT p.proname, has_function_privilege(current_user, p.oid, 'EXECUTE')
                       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                       WHERE n.nspname = 'public' AND p.proname LIKE 'sp\\_%' ORDER BY 1""")
        rotinas = cur.fetchall()
        sem_permissao = [nome for nome, pode in rotinas if not pode]
        if not rotinas:
            falha("Nenhuma procedure sp_* encontrada. O arquivo 01_criar_banco.sql foi executado?")
        elif sem_permissao:
            falha("Sem permissão de execução em: " + ", ".join(sem_permissao) + ". Rode 04_permissoes_aplicacao.sql e vincule o papel dgp_aplicacao ao login.")
        else:
            ok(f"{len(rotinas)} procedures acessíveis")

        # As permissões de escrita do papel são por coluna, por isso has_column_privilege.
        cur.execute("""SELECT has_table_privilege(current_user, 'public.usuario', 'SELECT'),
                              has_column_privilege(current_user, 'public.usuario', 'login', 'INSERT'),
                              has_column_privilege(current_user, 'public.cliente', 'documento', 'INSERT'),
                              has_column_privilege(current_user, 'public.cliente', 'documento', 'UPDATE')""")
        (ok if all(cur.fetchone()) else falha)("Permissões de leitura e escrita em usuario e cliente")

        cur.execute("SELECT count(*) FROM usuario WHERE perfil = 'ADMINISTRADOR' AND ativo")
        admins = cur.fetchone()[0]
        (ok if admins else falha)(f"{admins} administrador(es) ativo(s)")


def main():
    print("Verificando o ambiente do DGP...\n")
    verificar_python()
    verificar_pacotes()
    cfg = verificar_env()
    if cfg:
        try:
            verificar_banco(cfg)
        except ImportError:
            falha("psycopg não instalado. Rode: pip install -r requirements.txt")
    print()
    if falhas:
        print(f"{len(falhas)} problema(s) encontrado(s). Corrija e rode de novo.")
        sys.exit(1)
    print("Tudo certo! Rode: python run.py")


if __name__ == "__main__":
    main()
