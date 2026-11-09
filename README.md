# DGP — Dantas Gestão de Placas

Sistema web local (Flask + PostgreSQL) da Atividade 04 de PI 2026/02.
**Padrão do grupo:** Visual Studio Code · Python 3.13.x · PostgreSQL 17.x

## 1. Primeira execução (cada pessoa, no próprio computador)

1. **Banco:** siga o guia `GUIA PARA CRIAR E CONSULTAR O BANCO.txt` até rodar os arquivos `00` a `04`.
2. **Login da aplicação no PostgreSQL:** edite a senha em `docs/criar_login_aplicacao.sql` e execute no pgAdmin como `postgres`, conectado ao database `dgp`.
3. **Clonar e entrar na pasta** do repositório pelo terminal do VS Code.
4. **Ambiente virtual** (Windows PowerShell):
   ```
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
   Se o PowerShell bloquear: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e tente de novo.
5. **Dependências:** `pip install -r requirements.txt`
6. **Arquivo `.env`:** copie `.env.example` para `.env` e preencha `SECRET_KEY` e `DB_PASSWORD` (a senha do passo 2).
   Gere a chave com: `python -c "import secrets; print(secrets.token_hex(32))"`
7. **Conferir tudo:** `python scripts/verificar_ambiente.py` (precisa terminar com "Tudo certo!").
8. **Senha de um usuário de exemplo** (as senhas dos exemplos não são conhecidas):
   `python scripts/redefinir_senha.py ana.admin` (administrador) ou `bruno.operador` (funcionário).
9. **Rodar:** `python run.py` e abrir http://127.0.0.1:5000

> O `.env` guarda senhas e **nunca vai para o GitHub** (já está no `.gitignore`).
> Para cadastrar clientes com CPF/CNPJ fictício, coloque `VALIDAR_DIGITO_DOCUMENTO=0` no `.env`.

## 2. Estrutura e donos

```
app/
  __init__.py, config.py, db.py, seguranca.py, menu.py, util.py   (Gabriel)
  static/ (css, js, img)  e  templates/ (base, macros)            (Gabriel)
  modulos/
    autenticacao/  usuarios/  clientes/                            Gabriel (UC01, UC02, UC03)
    pedidos/                                                       Tatiane (UC04, UC05, UC08, UC09)
    pagamentos/  estoque/  relatorios/  painel/                    Jonathan (UC06, UC07, UC10, UC11, UC12)
scripts/  tests/  docs/  requirements.txt                          (Gabriel)
```

Cada pasta em `app/modulos/` é registrada **automaticamente**: basta ter um `routes.py` com um blueprint chamado `bp`.
Por isso ninguém precisa editar arquivos de outra pessoa.

## 3. Como construir o seu módulo

1. Substitua o `routes.py` do esqueleto da sua pasta (ele já mostra o formato).
2. Mantenha o nome do blueprint (ex.: `"pedidos"`) e uma rota chamada `index` — o menu lateral depende disso.
3. Coloque os templates em `app/modulos/<modulo>/templates/<modulo>/` e estenda `base.html`.
4. Use os componentes prontos de `_macros.html` (`cabecalho`, `campo`, `seletor`, `selo`, `paginacao`) e as classes do `app.css`.
5. **Banco** (`from app import db`): `db.todos(sql, params)`, `db.um(sql, params)`, `db.executar(sql, params)`.
   Pedidos, placas, pagamentos e estoque são gravados **somente pelas procedures**, por exemplo:
   `db.executar("CALL public.sp_cancelar_pedido(%s, %s)", (numero, motivo))`
6. **Erros do banco:** `db.traduzir_erro(exc)` devolve uma mensagem amigável; as mensagens das procedures (`RAISE EXCEPTION`) já vêm em português.
7. **Acesso:** `@login_required` ou `@perfil_required("ADMINISTRADOR")` (de `app.seguranca`). Usuário logado: `g.usuario`.
8. **Formulários POST** precisam do campo `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
9. UC04 pode usar `app.modulos.clientes.repo.buscar_para_selecao(termo)` para procurar o cliente.
10. Precisa de uma biblioteca nova ou de mudança em arquivo compartilhado? Avise o Gabriel.

## 4. Regras de GitHub

- A `main` nunca recebe commit direto: tudo entra por **pull request**.
- Uma branch por funcionalidade: `feat/uc04-registrar-pedido`.
- Commits pequenos, com prefixo `feat:`, `fix:` ou `docs:`.
- Antes de trabalhar: `git pull origin main` e atualize a sua branch.
- Revisão em rodízio: Tatiane revisa Jonathan, Jonathan revisa Gabriel, Gabriel revisa Tatiane.
- **Nunca enviar:** `.venv`, `__pycache__`, `.env`.
- Arquivos compartilhados e `requirements.txt` só o Gabriel altera.
- Fim de linha padronizado por `.gitattributes` e `.editorconfig`.

**Definição de pronto:** grava pela procedure, mostra o erro do banco quando falha, testado com os dados de exemplo e revisado por outra pessoa.

## 5. Testes

`python -m unittest discover -s tests -v` (não precisam do banco).

## 6. Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "SECRET_KEY ausente ou curta demais" | Preencha a `SECRET_KEY` no `.env` (mínimo 32 caracteres) |
| Página "Banco de dados indisponível" | Confira o serviço PostgreSQL, a porta e o `.env` |
| "permission denied" | Rode `04_permissoes_aplicacao.sql` e o `docs/criar_login_aplicacao.sql` |
| "Login ou senha inválidos" com usuário de exemplo | Use `scripts/redefinir_senha.py` |
| `Activate.ps1` bloqueado | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
