"""
Validadores reutilizaveis.

CPF hash agora usa HMAC-SHA256 com chave dedicada F (secret),
nao SHA256(salt+cpf) que eh enumeravel.
"""

import hmac
import re
from datetime import date
from hashlib import sha256

from django.core.exceptions import ValidationError
from stdnum.br import cpf as stdnum_cpf

from apps.core.encryption import _KeyRegistry


def validar_cpf(valor: str) -> None:
    """Valida CPF com algoritmo oficial. Aceita com ou sem mascara."""
    if not valor:
        raise ValidationError("CPF obrigatorio")
    limpo = re.sub(r"\D", "", valor)
    if len(limpo) != 11:
        raise ValidationError("CPF deve ter 11 digitos")
    if len(set(limpo)) == 1 or not stdnum_cpf.is_valid(limpo):
        raise ValidationError("CPF invalido")


def normalizar_cpf(valor: str) -> str:
    """Remove mascara, retorna 11 digitos."""
    return re.sub(r"\D", "", valor or "")


def formatar_cpf(valor: str) -> str:
    """Aplica mascara 000.000.000-00."""
    limpo = normalizar_cpf(valor)
    if len(limpo) != 11:
        return valor
    return f"{limpo[:3]}.{limpo[3:6]}.{limpo[6:9]}-{limpo[9:]}"


def hash_cpf(valor: str) -> str:
    """
    HMAC-SHA256(chave_F, CPF normalizado).

    Diferente de SHA-256(salt+cpf) porque:
    - Chave F eh secreta (Docker secret, nao hardcoded)
    - Espaco de CPFs (~200M) continua enumeravel, mas atacante precisa
      ter a chave F ALEM do banco vazado
    - Chave F pode ser rotacionada se vazar (mas requer recomputar todos
      os hashes de CPF - operacao controlada)
    """
    limpo = normalizar_cpf(valor)
    key = _KeyRegistry.get("F")
    return hmac.new(key, limpo.encode("utf-8"), sha256).hexdigest()


def validar_data_nascimento(valor: date) -> None:
    """Nao aceita data futura. Nao aceita > 120 anos atras."""
    if valor is None:
        raise ValidationError("Data de nascimento obrigatoria")
    hoje = date.today()
    if valor > hoje:
        raise ValidationError("Data de nascimento no futuro")
    idade = (hoje - valor).days / 365.25
    if idade > 120:
        raise ValidationError("Data de nascimento muito antiga")


def idade_em_anos(nascimento: date) -> int:
    """Idade completa em anos."""
    hoje = date.today()
    anos = hoje.year - nascimento.year
    if (hoje.month, hoje.day) < (nascimento.month, nascimento.day):
        anos -= 1
    return anos


def validar_crfa(valor: str) -> None:
    """Valida formato CRFa (UF-numero). Nao valida existencia real."""
    if not valor:
        return
    if not re.match(r"^[A-Z]{2}-\d{3,6}$", valor.upper()):
        raise ValidationError("CRFa invalido - use UF-numero (ex: MS-12345)")
