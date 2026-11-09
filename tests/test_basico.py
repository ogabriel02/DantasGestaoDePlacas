"""Testes das funcoes puras: senhas, documentos, mascaras e limite de tentativas."""
import base64
import hashlib
import time
import unittest

from app import seguranca, util


class TestSenhas(unittest.TestCase):
    def setUp(self):
        self._it = seguranca.ITERACOES
        seguranca.ITERACOES = 1000  # acelera os testes

    def tearDown(self):
        seguranca.ITERACOES = self._it

    def test_ida_e_volta(self):
        h = seguranca.gerar_hash("Senha@1234")
        self.assertTrue(h.startswith("pbkdf2_sha256$1000$"))
        self.assertTrue(seguranca.verificar_senha("Senha@1234", h))
        self.assertFalse(seguranca.verificar_senha("outra", h))

    def test_hashes_diferentes_para_mesma_senha(self):
        self.assertNotEqual(seguranca.gerar_hash("abc12345"), seguranca.gerar_hash("abc12345"))

    def test_aceita_salt_como_texto_ou_como_bytes_hex(self):
        salt = "4b327d4bee33c5ea9bd0b13fb5e62f83"
        for salt_bytes in (salt.encode(), bytes.fromhex(salt)):
            d = base64.b64encode(hashlib.pbkdf2_hmac("sha256", b"minhaSenha1", salt_bytes, 2000)).decode()
            self.assertTrue(seguranca.verificar_senha("minhaSenha1", f"pbkdf2_sha256$2000${salt}${d}"))

    def test_formatos_invalidos(self):
        for ruim in ("", "abc", "md5$1$a$b", "pbkdf2_sha256$x$a$b", "pbkdf2_sha256$99999999$a$b", None):
            self.assertFalse(seguranca.verificar_senha("x", ruim))
        self.assertFalse(seguranca.verificar_senha("x", seguranca.HASH_FALSO))

    def test_destino_seguro(self):
        self.assertEqual(seguranca.destino_seguro("/clientes?q=a"), "/clientes?q=a")
        for ruim in ("//evil.com", "https://evil.com", "evil.com", "", None, "/\\evil.com", "/a\\b"):
            self.assertIsNone(seguranca.destino_seguro(ruim))


class TestDocumentos(unittest.TestCase):
    def test_cpf(self):
        self.assertTrue(util.validar_cpf("529.982.247-25"))
        self.assertFalse(util.validar_cpf("111.111.111-11"))
        self.assertFalse(util.validar_cpf("11122233344"))
        self.assertFalse(util.validar_cpf("123"))

    def test_cnpj(self):
        self.assertTrue(util.validar_cnpj("11.222.333/0001-81"))
        self.assertFalse(util.validar_cnpj("11222333000199"))
        self.assertFalse(util.validar_cnpj("00000000000000"))

    def test_formatacao(self):
        self.assertEqual(util.formatar_documento("52998224725"), "529.982.247-25")
        self.assertEqual(util.formatar_documento("11222333000181"), "11.222.333/0001-81")
        self.assertEqual(util.formatar_telefone("34999990001"), "(34) 99999-0001")
        self.assertEqual(util.formatar_telefone("3433334444"), "(34) 3333-4444")
        self.assertEqual(util.formatar_cep("38400000"), "38400-000")
        self.assertEqual(util.formatar_documento(None), "")

    def test_escapar_like(self):
        self.assertEqual(util.escapar_like("50%_a\\"), "50\\%\\_a\\\\")


class TestLimiteTentativas(unittest.TestCase):
    def test_bloqueia_apos_cinco_falhas_e_libera_no_sucesso(self):
        chave = f"teste|{time.time()}"
        self.assertEqual(seguranca.segundos_bloqueado(chave), 0)
        for _ in range(4):
            seguranca.registrar_falha(chave)
        self.assertEqual(seguranca.segundos_bloqueado(chave), 0)
        seguranca.registrar_falha(chave)
        self.assertGreater(seguranca.segundos_bloqueado(chave), 0)
        seguranca.limpar_falhas(chave)
        self.assertEqual(seguranca.segundos_bloqueado(chave), 0)


if __name__ == "__main__":
    unittest.main()
