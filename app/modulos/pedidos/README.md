# Parte 2 — Pedidos (Tatiane)

Implementa UC04, UC05, UC08 e UC09 sobre a base Flask existente. As telas
estendem `base.html` e reutilizam seus componentes; CSS e JavaScript adicionais
ficam apenas neste módulo. Pagamentos são consultados no detalhe. Cobrança,
finalização, estoque, relatórios e painel continuam sob responsabilidade da parte 3.

## Executar

Siga o README da raiz para configurar PostgreSQL, dependências e `.env`.
Execute `python run.py`, entre como funcionário ou administrador e abra **Pedidos**.
Nenhuma alteração de estrutura do banco é necessária. O login da aplicação deve
pertencer ao papel `dgp_aplicacao` do script `04_permissoes_aplicacao.sql`.

## Fluxos

- `/pedidos/`: filtros combináveis por situação, cliente (nome ou documento),
  data exata de criação e parte do chassi; 15 pedidos por página.
- `/pedidos/novo`: busque o cliente pelo CPF/CNPJ completo antes de preencher o formulário, selecione
  o cadastro e informe chassi, tipo de veículo, posição, modelo, número, QR Codes
  e cores. A seleção começa vazia e a busca retorna somente o documento exato,
  com ou sem pontuação. Nome, documento parcial e busca vazia não consultam clientes.
- `/pedidos/<numero>`: dados do cliente, veículo, placas, autorização e pagamento.
- `/pedidos/<numero>/autorizacao`: POST com CSRF, executa `sp_definir_autorizacao`.
- `/pedidos/<numero>/cancelar`: confirmação com motivo obrigatório,
  executa `sp_cancelar_pedido`. As recusas do banco aparecem na tela.

O número da placa tem 7 caracteres e é obrigatório. Cada placa tem seu QR Code
obrigatório e exclusivo. Par gera dianteira e traseira com o mesmo número e
QR Codes distintos. Moto aceita somente traseira. O tipo de veículo é uma
informação do formulário; o esquema entregue armazena apenas o chassi em `veiculo`.

O fundo padrão é representado por `NULL`, conforme o banco, com caracteres
PRETA, VERMELHA, AZUL, VERDE ou DOURADA. Fundo COLECIONADOR aceita BRANCA ou
CINZA_PRATA. O modelo é obtido do cadastro real de `item_estoque`.

O veículo é cadastrado/reutilizado por chassi. Veículo, `sp_criar_pedido` e todas
as chamadas de `sp_adicionar_placa` usam a mesma transação. Qualquer falha desfaz
o cadastro inteiro, inclusive a primeira placa do par. Não há INSERT/UPDATE
direto em pedido ou placa. Não é feita reserva ou baixa de estoque nesta etapa.

O banco entregue não tem tabela de histórico de situação: o detalhe exibe criação,
última atualização e situação atual, sem inventar eventos anteriores. O cancelamento
não implementa estorno de pagamento, pois a procedure entregue não faz isso.

## Verificação

Execute `python -m unittest discover -s tests -v` na raiz.
Os testes de `tests/test_pedidos.py` verificam acesso, CSRF, cadastro com usuário
da sessão, validações, filtros, autorização, cancelamento, mensagens e rollback.

Roteiro manual para revisão da equipe:

1. Entrar como funcionário; conferir que Pedidos aparece ativo no menu.
2. Conferir que a seleção inicia vazia; buscar cliente pelo CPF/CNPJ completo,
   com e sem pontuação; registrar uma traseira e conferir o detalhe.
3. Registrar um par com dois QR Codes diferentes; conferir as duas posições.
4. Tentar par com QR Codes iguais, QR vazio e número vazio: nenhum pedido é salvo.
5. Escolher moto: dianteira e par devem ficar indisponíveis; enviar esses valores
   por POST também deve ser recusado.
6. Reutilizar o QR Code de outra placa no segundo QR de um novo par: o erro
   aparece e não são criados pedido, primeira placa ou veículo órfãos.
7. Alterar autorização e reabrir o detalhe para conferir a persistência.
8. Cancelar com motivo em branco: recusar. Informar motivo: cancelar e exibir
   o motivo na lista e no detalhe. Pedido encerrado não pode ser cancelado novamente.
9. Combinar os quatro filtros; conferir resultado vazio e paginação.
10. Conferir as quatro telas em celular e desktop.

Validação realizada nesta implementação: 54 testes passaram; integração em
PostgreSQL 17 temporário com os scripts entregues e o papel `dgp_aplicacao`
confirmou cadastro do par, consultas, autorização, cancelamento e rollback
integral por QR duplicado na segunda placa. As quatro telas foram verificadas
em navegador a 1440 px e 390 px. O runtime disponível para os testes foi Python
3.12; a equipe ainda deve executar a suíte no Python 3.13.x previsto no manual.
