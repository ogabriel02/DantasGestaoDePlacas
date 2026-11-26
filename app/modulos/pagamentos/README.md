# Parte 3 — Pagamentos, Estoque, Relatórios e Painel (Jonathan)

Implementa os casos de uso UC06, UC07, UC10, UC11 e UC12 sobre a base Flask existente:

- As telas estendem `base.html` e usam `_macros.html` e `app.css`.
- O CSS adicional fica no `static/` de cada módulo.
- Não há mudança na estrutura do banco nem biblioteca nova.

| Módulo | Casos de uso | Acesso | Endereço |
|---|---|---|---|
| `pagamentos/` | UC06 Controlar pagamentos, UC07 Finalizar pedido | Funcionário e administrador | `/pagamentos/` |
| `estoque/` | UC10 Gerenciar estoque | Somente administrador | `/estoque/` |
| `relatorios/` | UC11 Emitir relatórios | Somente administrador | `/relatorios/` |
| `painel/` | UC12 Painel e avisos (ver `painel/README.md`) | Funcionário e administrador | `/` |

## Regras de gravação

| Operação | Como grava |
|---|---|
| Gerar cobrança Pix | `CALL sp_gerar_cobranca(pedido, valor, 'PIX')` |
| Confirmar pagamento | `CALL sp_confirmar_pagamento(pedido)` |
| Finalizar pedido (baixa o estoque) | `CALL sp_finalizar_pedido(pedido)` + `CALL sp_gerar_avisos_estoque()`, mesma transação |
| Entrada e ajustes de estoque | `CALL sp_movimentar_estoque(item, tipo, qtd)` + `sp_gerar_avisos_estoque()`, mesma transação |
| Nível mínimo / novo modelo | `UPDATE`/`INSERT` em `item_estoque (modelo, nivel_minimo)`: não existe procedure, e o `04_permissoes_aplicacao.sql` libera essas colunas. Saldo inicial sempre zero, com entrada registrada pela procedure |
| Aviso de pedido parado / marcar lido | `INSERT`/`UPDATE` em `aviso` (colunas liberadas no `04`; não existe procedure) |
| Relatórios | somente `SELECT` |

- Não há `INSERT`/`UPDATE`/`DELETE` direto em `pedido`, `placa`, `pagamento` ou `movimentacao_estoque`.
- O saldo de estoque nunca é alterado diretamente.
- As validações de negócio continuam no banco; a tela apenas orienta.

## Mensagens do banco

`pagamentos/comum.py` deixa as mensagens das procedures, que vêm sem acento, mais claras. Exemplo: `Finalizacao exige autorizacao LIBERADA` vira *"O pedido só pode ser finalizado com a autorização externa liberada."*

- Uma mensagem nova, que não está na tabela, aparece como o banco enviou.
- Um erro que não vem do banco não é escondido.

## Tabela de preços (definida pela equipe)

O preço depende só da quantidade de placas do pedido, não do modelo. Fica em `pagamentos/precos.py`.

| Placas | Exemplos | Valor |
|---|---|---|
| 1 — individual | moto, só traseira ou só dianteira | R$ 180,00 |
| 2 — par | dianteira + traseira | R$ 250,00 |

- O valor é calculado no servidor; o formulário não envia valor.
- Forma de pagamento: somente Pix.

## Fluxos

**UC06 e UC07.** Em Pagamentos, abra o pedido.

1. **Criado:** "Gerar cobrança Pix". O pedido vai para *Aguardando pagamento*.
2. **Aguardando pagamento:** "Confirmar pagamento" depois de conferir o Pix no extrato. O pedido vai para *Em produção*.
3. **Em produção:** "Finalizar pedido". O pedido vai para *Finalizado* e as placas saem do estoque.

A tela mostra uma lista de conferência (pagamento, autorização liberada, 1 ou 2 placas, saldo suficiente), mas quem decide é a procedure.

**UC10.** Em Estoque:

- cartões de resumo, avisos de estoque baixo e a coluna "em pedidos abertos";
- no detalhe do modelo: entrada, ajuste para mais e para menos, nível mínimo e histórico;
- cadastro de novo modelo. Use "moto" no nome dos modelos de motocicleta e "automovel" nos de carro, porque o cadastro de pedidos usa o nome para conferir o tipo de veículo.

**UC11.** Em Relatórios:

- filtros: período (data de criação do pedido; padrão = mês atual), despachante, tipo de placa (modelo) e situação;
- visões: resumo por situação, por despachante, por tipo de placa e lista de pedidos;
- "Exportar CSV" abre direto no Excel: separador `;`, vírgula decimal, UTF-8 com BOM;
- textos que começam com `=`, `+`, `-` ou `@` são neutralizados contra fórmulas.

**UC12.** Veja `app/modulos/painel/README.md`: critério de pedido parado, `DIAS_PEDIDO_PARADO` e como agendar a rotina do ator Tempo no Windows.

## Verificação

```
python -m unittest discover -s tests -v
```

São 115 testes, sem banco. Os da Parte 3 ficam em:

- `tests/test_pagamentos.py`
- `tests/test_estoque.py`
- `tests/test_relatorios.py`
- `tests/test_painel.py`

Eles cobrem acesso (anônimo, funcionário e administrador), CSRF, validações, o `CALL` correto, mensagens do banco, transação única e rollback, e o conteúdo do CSV.

Integração executada em PostgreSQL 17 (Docker), com os scripts `00` a `04` (75/75) e o login no papel `dgp_aplicacao`:

- **Cobrança:** par a R$ 250 e moto a R$ 180. Repetir a cobrança ou confirmar fora da situação certa é recusado pelo banco.
- **Finalização:**
  - recusada sem autorização (pedido 3), sem placas (6) e sem estoque (7);
  - o pedido 8 é recusado e a baixa parcial é desfeita;
  - com sucesso, a baixa fica correta.
- **Estoque:**
  - entrada e ajustes funcionam; ajuste acima do saldo é recusado;
  - nível mínimo e cadastro de modelo funcionam, e os avisos não duplicam;
  - os saldos batem com o histórico.
- **Painel:**
  - cartões e pedidos parados corretos;
  - o comando `flask` cria os avisos sem duplicar;
  - permissões do funcionário e marcação de leitura funcionam.
- **Relatórios:** todas as visões e filtros conferidos contra SQL independente. O total de placas entregues é igual às saídas do estoque.

### Roteiro manual para a revisão

1. Como **funcionário**:
   - Pagamentos abre;
   - Estoque e Relatórios não aparecem no menu e dão "Acesso negado" pelo endereço.
2. Pedido criado com uma placa: a cobrança é de R$ 180,00. Com par: R$ 250,00. Pedido sem placas: o botão fica desabilitado.
3. Gerar a cobrança e confirmar: o pedido vai para *Em produção*.
4. Finalizar sem a autorização liberada: aparece a mensagem do banco. Liberar a autorização no pedido e finalizar: o saldo do modelo cai no Estoque.
5. Como **administrador**, fazer um ajuste para menos maior que o saldo: o banco recusa. Fazer uma entrada: o saldo sobe e aparece no histórico.
6. Subir o nível mínimo acima do saldo: surge um aviso no Painel e no Estoque.
7. "Gerar avisos agora" no Painel e "Marcar como lido".
8. Relatórios: trocar as visões e os filtros e exportar o CSV para o Excel.
