"""Carrinho espelhado na URL (secao 2.2 da ARQUITETURA).

Regra: session_state e cache rapido, query_params e persistencia.
Escreve nos dois, le do query_params quando o session_state esta vazio.

O parser e serializador nao dependem de streamlit, entao dao para testar
sem subir o app. So as duas funcoes do fim tocam o runtime.
"""
from __future__ import annotations

import streamlit as st

CHAVE_URL = "c"
CHAVE_PORTE = "porte"


def desserializar(bruto: str) -> dict[int, int]:
    """'3x1,7x2' -> {3: 1, 7: 2}. Lixo na URL e ignorado, nunca quebra."""
    itens: dict[int, int] = {}
    for parte in filter(None, (bruto or "").split(",")):
        try:
            sid, qtd = parte.split("x")
            sid_i, qtd_i = int(sid), int(qtd)
        except ValueError:
            continue
        if sid_i > 0 and qtd_i > 0:
            itens[sid_i] = min(qtd_i, 9)
    return itens


def serializar(itens: dict[int, int]) -> str:
    return ",".join(f"{k}x{v}" for k, v in sorted(itens.items()) if v > 0)


def carregar_carrinho() -> dict[int, int]:
    """Le o carrinho da URL. Formato: ?c=3x1,7x2"""
    if CHAVE_URL in st.query_params:
        itens = desserializar(st.query_params.get(CHAVE_URL, ""))
        st.session_state.carrinho = itens
        return itens
    return st.session_state.get("carrinho", {})


def salvar_carrinho(itens: dict[str, int] | dict[int, int]) -> None:
    itens = {int(k): int(v) for k, v in itens.items() if int(v) > 0}
    if itens:
        st.query_params[CHAVE_URL] = serializar(itens)
    else:
        st.query_params.pop(CHAVE_URL, None)
    st.session_state.carrinho = itens


def alterar(servico_id: int, delta: int) -> dict[int, int]:
    itens = dict(carregar_carrinho())
    novo = itens.get(servico_id, 0) + delta
    if novo <= 0:
        itens.pop(servico_id, None)
    else:
        itens[servico_id] = min(novo, 9)
    salvar_carrinho(itens)
    return itens


def escolher_servico(servico_id: int) -> dict[int, int]:
    """O catalogo e de niveis: escolher um troca o anterior, nao soma."""
    salvar_carrinho({servico_id: 1})
    return {servico_id: 1}


def carregar_porte(padrao: str = "carro") -> str:
    """Porte do veiculo, tambem espelhado na URL: ?porte=suv"""
    if CHAVE_PORTE in st.query_params:
        valor = st.query_params.get(CHAVE_PORTE, "")
        st.session_state.porte = valor
        return valor
    return st.session_state.get("porte", padrao)


def salvar_porte(codigo: str) -> None:
    st.query_params[CHAVE_PORTE] = codigo
    st.session_state.porte = codigo


def limpar() -> None:
    salvar_carrinho({})
    st.query_params.pop(CHAVE_PORTE, None)
    st.session_state.pop("porte", None)
