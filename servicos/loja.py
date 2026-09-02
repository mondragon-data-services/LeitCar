"""Dados da loja e chaves sensiveis, sempre vindos de st.secrets.

Chave PIX, nome do recebedor e cidade ficam em st.secrets, nunca no codigo
(secao 11 da ARQUITETURA). Aqui so ficam os defaults de vitrine.
"""
from __future__ import annotations

import streamlit as st

PADRAO = {
    "nome": "Leite Estética Automotiva",
    "telefone": "14998904665",
    "endereco": "Duartina - SP",
    "cidade": "Duartina",
    "chamada": "Lavagem, detalhamento e higienização com acabamento "
               "de loja especializada.",
    "url_publica": "http://localhost:8501",
}


def _bloco(nome: str) -> dict:
    try:
        return dict(st.secrets.get(nome, {}))
    except Exception:                 # sem secrets.toml, roda com os defaults
        return {}


def info() -> dict:
    return {**PADRAO, **_bloco("loja")}


def pix() -> dict:
    """Vazio = sem cobranca antecipada, pagamento na entrega.

    Sugestao da secao 2.4: comece cobrando so um sinal, ou nada.
    """
    cfg = _bloco("pix")
    if not cfg.get("chave"):
        return {}
    return {
        "chave": cfg["chave"],
        "nome": cfg.get("nome", info()["nome"]),
        "cidade": cfg.get("cidade", info()["cidade"]),
        "sinal_centavos": int(cfg.get("sinal_centavos", 2000)),
        "centavos_unicos": bool(cfg.get("centavos_unicos", True)),
    }


def senha_admin() -> str:
    return str(_bloco("admin").get("senha", ""))
