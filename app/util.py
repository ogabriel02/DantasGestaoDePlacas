"""Funcoes de apoio: documentos, mascaras e listas fixas."""
import re

UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
       "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]

PERFIS = {"FUNCIONARIO": "Funcionário", "ADMINISTRADOR": "Administrador"}
TIPOS_PESSOA = {"PF": "Pessoa física", "PJ": "Pessoa jurídica"}
CATEGORIAS = {"PARTICULAR": "Particular", "DESPACHANTE": "Despachante"}


def so_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def validar_cpf(valor):
    cpf = so_digitos(valor)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[n]) * (i + 1 - n) for n in range(i))
        if (soma * 10 % 11) % 10 != int(cpf[i]):
            return False
    return True


def validar_cnpj(valor):
    cnpj = so_digitos(valor)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def digito(base):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(base) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    return digito(cnpj[:12]) == int(cnpj[12]) and digito(cnpj[:13]) == int(cnpj[13])


def formatar_documento(valor):
    d = so_digitos(valor)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    if len(d) == 14:
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return valor or ""


def formatar_telefone(valor):
    d = so_digitos(valor)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return valor or ""


def formatar_cep(valor):
    d = so_digitos(valor)
    return f"{d[:5]}-{d[5:]}" if len(d) == 8 else (valor or "")


def escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
