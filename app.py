"""Leite Estetica Automotiva :: roteamento sem rotas (secao 8 da ARQUITETURA).

O Streamlit nao tem URL de verdade, entao quem decide o que mostrar sao
os query params. A sidebar fica escondida no fluxo do cliente: ela
entrega que aquilo e um Streamlit e confunde quem so quer agendar.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="Leite Estética Automotiva", page_icon="🚿",
                   layout="centered", initial_sidebar_state="collapsed")

from paginas import (admin_agenda, admin_horarios, admin_portfolio,  # noqa: E402
                     admin_servicos, agendar, comprovante, ui, vitrine)
from servicos import db, loja  # noqa: E402


def autenticado() -> bool:
    return bool(st.session_state.get("admin_ok"))


def tela_login() -> None:
    ui.aplicar_estilo()
    st.title("Área do dono")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        esperada = loja.senha_admin()
        if esperada and senha == esperada:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    if not loja.senha_admin():
        st.warning("Nenhuma senha configurada em .streamlit/secrets.toml "
                   "([admin] senha = \"...\").")
    if st.button("← Voltar para o site"):
        st.query_params.clear()
        st.rerun()


def main() -> None:
    # Cria o schema no primeiro boot. Em hospedagem sem shell (Streamlit
    # Cloud) e a unica chance de rodar o SQL; e idempotente, entao nas
    # vezes seguintes nao custa nada.
    try:
        db.garantir_schema()
    except Exception as e:
        st.error("Nao consegui falar com o banco de dados.")
        st.caption("Confira `[connections.postgresql] url` nos secrets do app.")
        st.exception(e)
        st.stop()

    if codigo := st.query_params.get("pedido"):
        comprovante.render(codigo)
        st.stop()

    if st.query_params.get("area") == "admin":
        if not autenticado():
            tela_login()
            st.stop()
        # url_path explicito: as paginas do admin expoem um callable chamado
        # `render`, e sem isso o st.navigation infere o mesmo pathname
        # para todas e recusa a lista.
        pg = st.navigation([
            st.Page(admin_agenda.render, title="Agenda", icon="📅",
                    url_path="agenda", default=True),
            st.Page(admin_servicos.render, title="Serviços", icon="🧽",
                    url_path="servicos"),
            st.Page(admin_horarios.render, title="Horários", icon="🕗",
                    url_path="horarios"),
            st.Page(admin_portfolio.render, title="Portfólio", icon="📸",
                    url_path="portfolio"),
        ])
        with st.sidebar:
            st.caption("Leite Estética · admin")
            if st.button("Sair", width="stretch"):
                st.session_state.admin_ok = False
                st.query_params.clear()
                st.rerun()
        pg.run()
        st.stop()

    if st.query_params.get("p") == "agendar":
        agendar.render()
        st.stop()

    vitrine.render()


main()
