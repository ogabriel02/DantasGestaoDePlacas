# Painel e avisos (UC12) — Jonathan

Página inicial depois do login (`/`).

- **Cartões** com o total de pedidos por situação. Cada cartão abre a lista de Pagamentos filtrada por aquela situação.
- **Avisos não lidos.** O botão "Ver também os lidos" mostra os 50 avisos mais recentes. "Marcar como lido" grava `lido` e `lido_em`.
  - O funcionário vê e marca apenas avisos de pedido.
  - Avisos de estoque são do administrador.
- **Pedidos parados:** pedidos em aberto (nem finalizados nem cancelados) sem atualização há mais de N dias. A lista é calculada na hora; a coluna "sem aviso aberto" indica os que ainda não têm aviso.
- **Estoque** (só para o administrador): quantos modelos estão disponíveis, no mínimo e esgotados.

## Critério de pedido parado

Situação diferente de `FINALIZADO` e `CANCELADO`, e `pedido.atualizado_em` mais antigo que N dias.
O campo é atualizado pelo trigger `bu_pedido_atualizado` a cada alteração no pedido (cobrança, confirmação, autorização, placas).

N vem do `.env` (padrão 3, aceito de 1 a 365):

```
DIAS_PEDIDO_PARADO=3
```

## Rotina do ator Tempo

Ela faz duas coisas, numa única transação:

1. Cria um aviso `PEDIDO_PARADO` para cada pedido parado que ainda não tem aviso não lido. O banco não tem procedure para isso, então a gravação é um `INSERT` em `aviso`, coluna liberada pelo `04_permissoes_aplicacao.sql`; o `02_dados_exemplo.sql` faz o mesmo.
2. Chama `sp_gerar_avisos_estoque()`.

Não gera avisos repetidos. Se o aviso for lido e o pedido continuar parado, a próxima execução cria um novo lembrete.

Formas de executar:

- **Botão "Gerar avisos agora"** no Painel (somente administrador).
- **Comando de linha**, com a `.venv` ativa, na pasta do projeto:
  ```
  flask --app run painel gerar-avisos
  flask --app run painel gerar-avisos --dias 5
  ```

### Agendar no Windows (Agendador de Tarefas)

Rodar uma vez, no PowerShell, trocando `C:\caminho\DantasGestaoDePlacas` pela pasta do projeto.
O exemplo executa todo dia às 8h:

```
schtasks /Create /TN "DGP - gerar avisos" /SC DAILY /ST 08:00 /TR "\"C:\caminho\DantasGestaoDePlacas\.venv\Scripts\flask.exe\" --app \"C:\caminho\DantasGestaoDePlacas\run.py\" painel gerar-avisos"
```

- Conferir: `schtasks /Query /TN "DGP - gerar avisos"`
- Testar agora: `schtasks /Run /TN "DGP - gerar avisos"`
- Remover: `schtasks /Delete /TN "DGP - gerar avisos" /F`

O comando usa o `.env` da pasta do projeto, então o PostgreSQL precisa estar ligado no horário agendado.
