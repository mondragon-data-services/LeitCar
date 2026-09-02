"""Catalogo, porte do veiculo e portfolio (Fase 2).

O catalogo e de niveis: o cliente escolhe um servico, nao monta uma
cesta. O preco da tabela e para carro de passeio, e o porte do veiculo
soma um acrescimo por cima.

A escolha vive dentro de um @st.fragment: trocar de servico ou de porte
reroda so esse bloco, nao a pagina inteira.
"""
from __future__ import annotations

import streamlit as st

from paginas import ui
from servicos import agenda, carrinho, db, formato


def render() -> None:
    ui.aplicar_estilo()
    ui.cabecalho()

    servicos = db.listar_servicos()
    if not servicos:
        st.info("Nenhum serviço cadastrado ainda.")
        return

    ui.secao("Tabela de preços", "Escolha o serviço")
    _catalogo(servicos, db.itens_por_servico(), db.listar_portes())

    _portfolio()
    ui.rodape()


@st.fragment
def _catalogo(servicos: list[dict], inclusos: dict[int, list[str]],
              portes: list[dict]) -> None:
    itens = carrinho.carregar_carrinho()
    mapa = {int(s["id"]): s for s in servicos}
    escolhido = next((sid for sid in itens if sid in mapa), None)

    porte_codigo = carrinho.carregar_porte()
    codigos = [p["codigo"] for p in portes]
    if porte_codigo not in codigos:
        porte_codigo = codigos[0] if codigos else "carro"
    porte = next((p for p in portes if p["codigo"] == porte_codigo), None)
    acrescimo = int(porte["acrescimo_centavos"]) if porte else 0

    for s in servicos:
        sid = int(s["id"])
        selecionado = sid == escolhido
        with st.container(border=True):
            topo, valor = st.columns([3, 2], vertical_alignment="top")
            with topo:
                marca = ("<span class='lc-escolhido'>Escolhido</span><br>"
                         if selecionado else "")
                bullets = "".join(f"<li>{d}</li>" for d in inclusos.get(sid, []))
                st.markdown(
                    f"{marca}<p class='lc-nome'>{s['nome']}</p>"
                    f"<p class='lc-sub'>{s['descricao']}</p>"
                    f"<ul class='lc-inclui'>{bullets}</ul>",
                    unsafe_allow_html=True)
            with valor:
                preco = int(s["preco_centavos"]) + acrescimo
                extra = (f"<small>{formato.reais(int(s['preco_centavos']))} "
                         f"+ {formato.reais(acrescimo)} {porte['nome']}</small>"
                         if acrescimo else "<small>carro de passeio</small>")
                st.markdown(
                    f"<div class='lc-preco'>{formato.reais(preco)}<br>{extra}</div>"
                    f"<div class='lc-meta'>⏱ "
                    f"{formato.duracao_humana(int(s['duracao_min']))}</div>",
                    unsafe_allow_html=True)
                if selecionado:
                    if st.button("Remover", key=f"rm{sid}", width="stretch"):
                        carrinho.limpar()
                        ui.rerun_bloco()
                elif st.button("Escolher", key=f"add{sid}", type="primary",
                               width="stretch"):
                    carrinho.escolher_servico(sid)
                    carrinho.salvar_porte(porte_codigo)
                    ui.rerun_bloco()

    _porte(portes, porte_codigo)
    _rodape_total(mapa, itens, acrescimo, porte)


def _porte(portes: list[dict], atual: str) -> None:
    """O acrescimo por porte muda o preco de todos os servicos de uma vez."""
    if not portes:
        return
    rotulos = {
        p["codigo"]: (p["nome"] if not int(p["acrescimo_centavos"])
                      else f"{p['nome']} (+{formato.reais(int(p['acrescimo_centavos']))})")
        for p in portes
    }
    codigos = list(rotulos)
    novo = st.radio("Porte do veículo", codigos, horizontal=True,
                    index=codigos.index(atual) if atual in codigos else 0,
                    format_func=lambda c: rotulos[c], key="radio_porte")
    if novo != atual:
        carrinho.salvar_porte(novo)
        ui.rerun_bloco()


def _rodape_total(mapa: dict[int, dict], itens: dict[int, int],
                  acrescimo: int, porte: dict | None) -> None:
    if not itens:
        st.caption("Escolha um serviço acima para ver os horários livres.")
        return

    total = agenda.total_centavos(mapa, itens) + acrescimo
    duracao = agenda.duracao_total(mapa, itens)

    st.markdown("<div class='lc-barra'></div>", unsafe_allow_html=True)
    esq, dir_ = st.columns([3, 2], vertical_alignment="center")
    esq.markdown(
        f"<span class='lc-preco'>{formato.reais(total)}</span><br>"
        f"<span class='lc-meta'>{porte['nome'] if porte else ''} · "
        f"{formato.duracao_humana(duracao)} de serviço</span>",
        unsafe_allow_html=True)
    if dir_.button("Escolher horário", type="primary", width="stretch"):
        ui.ir_para(p="agendar")


def _portfolio() -> None:
    """Nossos trabalhos. Sem foto nenhuma, a secao some da tela do cliente."""
    fotos = db.listar_portfolio(limite=12)
    if not fotos:
        return
    # Em hospedagem com disco efemero a pasta static/ some no deploy;
    # o banco repoe o que faltar antes de a grade pedir as imagens.
    db.materializar_fotos()
    ui.secao("Portfólio", "Trabalhos que saíram daqui")
    st.caption("Toque numa foto para ver em tamanho grande.")
    grade = ui.galeria_html(fotos)
    if grade:
        st.markdown(grade, unsafe_allow_html=True)
