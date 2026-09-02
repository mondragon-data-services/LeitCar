"""Tabela de precos: servicos, o que esta incluso e acrescimo por porte.

Preco em centavos inteiros no banco; aqui as colunas aparecem em reais
para o dono nao ter que pensar em centavos.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from servicos import db, formato

COLUNAS = ["id", "nome", "descricao", "preco", "duracao_min", "ativo", "ordem"]


def render() -> None:
    st.title("Tabela de preços")

    _servicos()
    st.divider()
    _inclusos()
    st.divider()
    _portes()


def _servicos() -> None:
    st.subheader("Serviços")
    st.caption("Preços referentes a carro de passeio. Reajuste não mexe em "
               "pedido antigo: o item guarda o preço do dia da compra.")

    linhas = db.listar_servicos(incluir_inativos=True)
    df = pd.DataFrame(linhas or [], columns=[
        "id", "nome", "descricao", "preco_centavos", "duracao_min", "ativo", "ordem"])
    df["preco"] = (df["preco_centavos"].fillna(0) / 100).astype(float) if not df.empty else []

    editado = st.data_editor(
        df[COLUNAS] if not df.empty else pd.DataFrame(columns=COLUNAS),
        num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "id": st.column_config.NumberColumn("id", disabled=True, width="small"),
            "nome": st.column_config.TextColumn("Serviço", required=True),
            "descricao": st.column_config.TextColumn("Chamada", width="large"),
            "preco": st.column_config.NumberColumn("Preço (R$)", min_value=0.0,
                                                   step=10.0, format="%.2f"),
            "duracao_min": st.column_config.NumberColumn("Duração (min)", min_value=15,
                                                         step=15),
            "ativo": st.column_config.CheckboxColumn("Ativo"),
            "ordem": st.column_config.NumberColumn("Ordem", step=1),
        },
        key="editor_servicos",
    )

    if st.button("Salvar serviços", type="primary"):
        registros = []
        for r in editado.to_dict("records"):
            if not (r.get("nome") or "").strip():
                continue
            registros.append({
                "id": r.get("id"),
                "nome": r["nome"],
                "descricao": r.get("descricao") or "",
                "preco_centavos": int(round(float(r.get("preco") or 0) * 100)),
                "duracao_min": int(r.get("duracao_min") or 60),
                "ativo": bool(r.get("ativo", True)),
                "ordem": int(r.get("ordem") or 0),
            })
        db.salvar_servicos(registros)
        st.success("Serviços salvos.")
        st.rerun()


def _inclusos() -> None:
    """A lista de bullets que aparece no card de cada servico na vitrine."""
    st.subheader("O que está incluso")
    st.caption("Uma linha por item. É o que o cliente lê no card do serviço.")

    inclusos = db.itens_por_servico()
    for s in db.listar_servicos(incluir_inativos=True):
        sid = int(s["id"])
        with st.expander(f"{s['nome']} — {len(inclusos.get(sid, []))} item(ns)"):
            texto = st.text_area("Itens", value="\n".join(inclusos.get(sid, [])),
                                 height=150, key=f"inc{sid}",
                                 label_visibility="collapsed")
            if st.button("Salvar itens", key=f"btninc{sid}"):
                db.salvar_itens_servico(sid, texto.splitlines())
                st.success("Itens salvos.")
                st.rerun()


def _portes() -> None:
    st.subheader("Acréscimo por porte")
    st.warning("Os valores de SUV e caminhonete vieram como **provisórios** da "
               "especificação: a tabela manuscrita diz só \"valor tem acréscimo\", "
               "sem número. Confirme com o Leite e corrija aqui.", icon="⚠️")

    linhas = db.listar_portes(incluir_inativos=True)
    df = pd.DataFrame(linhas or [], columns=["codigo", "nome", "acrescimo_centavos",
                                             "ordem", "ativo"])
    df["acrescimo"] = ((df["acrescimo_centavos"].fillna(0) / 100).astype(float)
                       if not df.empty else [])

    colunas = ["codigo", "nome", "acrescimo", "ordem", "ativo"]
    editado = st.data_editor(
        df[colunas] if not df.empty else pd.DataFrame(columns=colunas),
        num_rows="dynamic", width="stretch", hide_index=True,
        column_config={
            "codigo": st.column_config.TextColumn("Código", required=True,
                                                  help="carro, suv, caminhonete"),
            "nome": st.column_config.TextColumn("Porte", required=True),
            "acrescimo": st.column_config.NumberColumn("Acréscimo (R$)", min_value=0.0,
                                                       step=10.0, format="%.2f"),
            "ordem": st.column_config.NumberColumn("Ordem", step=1),
            "ativo": st.column_config.CheckboxColumn("Ativo"),
        },
        key="editor_portes",
    )

    if st.button("Salvar portes", type="primary"):
        db.salvar_portes([{
            "codigo": r.get("codigo"),
            "nome": r.get("nome"),
            "acrescimo_centavos": int(round(float(r.get("acrescimo") or 0) * 100)),
            "ordem": int(r.get("ordem") or 0),
            "ativo": bool(r.get("ativo", True)),
        } for r in editado.to_dict("records") if (r.get("codigo") or "").strip()])
        st.success("Portes salvos.")
        st.rerun()

    servicos = db.listar_servicos()
    portes = db.listar_portes()
    if servicos and portes:
        st.caption("Como fica a tabela para o cliente:")
        st.dataframe(pd.DataFrame([
            {"Serviço": s["nome"],
             **{p["nome"]: formato.reais(int(s["preco_centavos"])
                                         + int(p["acrescimo_centavos"]))
                for p in portes}}
            for s in servicos
        ]), width="stretch", hide_index=True)
