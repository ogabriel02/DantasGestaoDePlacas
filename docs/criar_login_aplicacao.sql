-- Execute como administrador (ex.: postgres), conectado ao database dgp,
-- DEPOIS de rodar 04_permissoes_aplicacao.sql.
-- Cada pessoa cria o login no PostgreSQL do proprio computador.
-- Troque a senha abaixo e use a mesma no arquivo .env (DB_PASSWORD).

CREATE ROLE dgp_app LOGIN PASSWORD 'boblolita';
GRANT dgp_aplicacao TO dgp_app;
