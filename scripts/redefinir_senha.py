"""Define uma nova senha para um usuario existente (ex.: os usuarios de exemplo).

Uso:
  python scripts/redefinir_senha.py ana.admin            # grava no banco
  python scripts/redefinir_senha.py --so-hash            # apenas imprime o hash
"""
import getpass
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from app.config import carregar_config  # noqa: E402
from app.seguranca import gerar_hash  # noqa: E402


def ler_senha():
    senha = getpass.getpass("Nova senha (mínimo 8 caracteres): ")
    if len(senha) < 8:
        sys.exit("A senha precisa ter pelo menos 8 caracteres.")
    if senha != getpass.getpass("Repita a senha: "):
        sys.exit("As senhas não conferem.")
    return senha


def main():
    args = sys.argv[1:]
    if args == ["--so-hash"]:
        print(gerar_hash(ler_senha()))
        return
    if len(args) != 1 or args[0].startswith("-"):
        sys.exit(__doc__)

    import psycopg

    login, cfg = args[0].strip().lower(), carregar_config()
    senha_hash = gerar_hash(ler_senha())
    with psycopg.connect(
        host=cfg["DB_HOST"], port=cfg["DB_PORT"], dbname=cfg["DB_NAME"],
        user=cfg["DB_USER"], password=cfg["DB_PASSWORD"], connect_timeout=5,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE usuario SET senha_hash = %s WHERE login = %s", (senha_hash, login))
            if cur.rowcount == 0:
                sys.exit(f"Usuário '{login}' não encontrado.")
    print(f"Senha de '{login}' atualizada.")


if __name__ == "__main__":
    main()
