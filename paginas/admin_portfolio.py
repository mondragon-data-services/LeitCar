"""Galeria do portfolio: upload, legenda, ordem e exclusao (Fase 5).

Toda foto que entra passa pelo `servicos/portfolio.py`, que corrige a
orientacao do EXIF, redimensiona e recomprime. Foto de celular chega com
4 MB e sai com uns 200 KB, senao a vitrine ficaria pesada no 4G.
"""
from __future__ import annotations

import streamlit as st

from servicos import db, portfolio

TIPOS = ["jpg", "jpeg", "png", "webp", "heic", "heif", "bmp", "tif", "tiff"]


def render() -> None:
    st.title("Portfólio")
    st.caption("As fotos aqui aparecem na seção *Trabalhos que saíram daqui* "
               "da vitrine e na landing do Google.")

    db.materializar_fotos()
    _upload()
    _importar_da_pasta()
    st.divider()
    _galeria()


def _upload() -> None:
    arquivos = st.file_uploader(
        "Enviar fotos", type=TIPOS, accept_multiple_files=True,
        help="Pode mandar várias de uma vez. JPG, PNG, WEBP ou HEIC do iPhone.",
        key=f"upload_{st.session_state.get('upload_rodada', 0)}")
    if not arquivos:
        return

    servicos = db.listar_servicos(incluir_inativos=True)
    opcoes = {0: "— sem serviço —"} | {int(s["id"]): s["nome"] for s in servicos}
    col_a, col_b = st.columns([2, 1])
    legenda = col_a.text_input("Legenda para todas (opcional)",
                               placeholder="Ex.: Hilux — detalhamento completo")
    servico_id = col_b.selectbox("Serviço", list(opcoes), format_func=opcoes.get)

    if st.button(f"Adicionar {len(arquivos)} foto(s) à galeria",
                 type="primary", width="stretch"):
        novas, repetidas, falhas = 0, 0, []
        for up in arquivos:
            try:
                arquivo = portfolio.salvar(up.getvalue(), up.name)
            except portfolio.ImagemInvalida as e:
                falhas.append(f"{up.name}: {e}")
                continue
            if db.adicionar_foto(arquivo, legenda.strip(), servico_id or None):
                novas += 1
            else:
                repetidas += 1

        if novas:
            st.success(f"{novas} foto(s) adicionada(s).")
        if repetidas:
            st.info(f"{repetidas} já estavam na galeria e foram ignoradas.")
        for f in falhas:
            st.error(f)
        # Troca a key do uploader para ele voltar vazio no proximo rerun.
        st.session_state.upload_rodada = st.session_state.get("upload_rodada", 0) + 1
        st.rerun()


def _importar_da_pasta() -> None:
    """Atalho para quem largou as fotos direto na pasta `fotos/`."""
    pendentes = portfolio.listar_pendentes()
    if not pendentes:
        return
    with st.container(border=True):
        st.markdown(f"**{len(pendentes)} foto(s) na pasta `fotos/`** — "
                    "dá para importar de uma vez.")
        st.caption(", ".join(p.name for p in pendentes[:8])
                   + (" ..." if len(pendentes) > 8 else ""))
        if st.button("Importar tudo da pasta fotos/", width="stretch"):
            novas = 0
            for arquivo, nome_original in portfolio.importar_pasta():
                if db.adicionar_foto(arquivo, "", None):
                    novas += 1
            st.success(f"{novas} foto(s) importada(s).")
            st.rerun()


def _galeria() -> None:
    fotos = db.listar_portfolio(incluir_inativos=True)
    if not fotos:
        st.info("Nenhuma foto ainda. Envie a primeira acima, ou largue os "
                "arquivos na pasta `fotos/` do projeto.")
        return

    servicos = db.listar_servicos(incluir_inativos=True)
    opcoes = {0: "— sem serviço —"} | {int(s["id"]): s["nome"] for s in servicos}
    st.subheader(f"{len(fotos)} foto(s)")

    alteracoes = []
    for f in fotos:
        with st.container(border=True):
            img, campos = st.columns([1, 3], vertical_alignment="top")
            dados = portfolio.bytes_de(f["arquivo"], thumb=True)
            if dados:
                img.image(dados, width="stretch")
            else:
                img.warning("arquivo sumiu")

            with campos:
                a, b = st.columns([3, 2])
                legenda = a.text_input("Legenda", value=f["legenda"] or "",
                                       key=f"lg{f['id']}")
                atual = int(f["servico_id"]) if f["servico_id"] else 0
                servico_id = b.selectbox(
                    "Serviço", list(opcoes), format_func=opcoes.get,
                    index=list(opcoes).index(atual) if atual in opcoes else 0,
                    key=f"sv{f['id']}")
                c, d, e = st.columns([1, 1, 1])
                ordem = c.number_input("Ordem", value=int(f["ordem"] or 0),
                                       step=1, key=f"or{f['id']}")
                ativo = d.checkbox("Visível", value=bool(f["ativo"]),
                                   key=f"at{f['id']}")
                if e.button("Excluir", key=f"del{f['id']}", width="stretch"):
                    arquivo = db.remover_foto(int(f["id"]))
                    if arquivo:
                        portfolio.remover(arquivo)
                    st.rerun()

            alteracoes.append({"id": int(f["id"]), "legenda": legenda,
                               "servico_id": servico_id or None,
                               "ordem": int(ordem), "ativo": bool(ativo)})

    if st.button("Salvar alterações", type="primary"):
        db.salvar_portfolio(alteracoes)
        st.success("Galeria atualizada.")
        st.rerun()
