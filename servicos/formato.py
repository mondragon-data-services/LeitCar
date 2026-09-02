"""Formatacao de dinheiro, telefone, placa e codigo de pedido.

Nada aqui importa streamlit: e regra de negocio, tem que sobreviver
a uma troca de camada de tela (secao 14 da ARQUITETURA).
"""
from __future__ import annotations

import re
import secrets as _secrets

ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sem I, O, 0, 1


def reais(centavos: int) -> str:
    """3500 -> 'R$ 35,00'"""
    return f"R$ {centavos / 100:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def duracao_humana(minutos: int) -> str:
    """90 -> '1h30'"""
    if minutos < 60:
        return f"{minutos} min"
    horas, resto = divmod(minutos, 60)
    return f"{horas}h" if resto == 0 else f"{horas}h{resto:02d}"


def so_digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto or "")


def normalizar_telefone(texto: str) -> str:
    """Devolve so digitos com DDD. Vazio quando invalido."""
    d = so_digitos(texto)
    if d.startswith("55") and len(d) > 11:
        d = d[2:]
    return d if 10 <= len(d) <= 11 else ""


def telefone_humano(digitos: str) -> str:
    d = so_digitos(digitos)
    if len(d) == 11:
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    if len(d) == 10:
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return digitos


def telefone_wa(digitos: str) -> str:
    """Formato aceito pelo wa.me: 55 + DDD + numero."""
    d = so_digitos(digitos)
    return d if d.startswith("55") else f"55{d}"


def normalizar_placa(texto: str) -> str:
    """Aceita ABC1234 e ABC1D23 (Mercosul). Vazio quando invalido."""
    p = re.sub(r"[^A-Za-z0-9]", "", texto or "").upper()
    if re.fullmatch(r"[A-Z]{3}\d{4}", p) or re.fullmatch(r"[A-Z]{3}\d[A-Z]\d{2}", p):
        return p
    return ""


def placa_humana(placa: str) -> str:
    return f"{placa[:3]}-{placa[3:]}" if len(placa) == 7 else placa


def gerar_codigo(tamanho: int = 4) -> str:
    """LC + 4 caracteres. Ex.: LC7F3K."""
    return "LC" + "".join(_secrets.choice(ALFABETO_CODIGO) for _ in range(tamanho))
