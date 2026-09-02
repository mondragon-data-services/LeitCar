"""Data, slots e dados do cliente (Fases 3 e 4).

A duracao muda conforme o carrinho, entao os slots sao recalculados
sempre que o carrinho muda. Nunca venda um slot de 30 min para um
servico de 2 horas.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import streamlit as st

from paginas import ui
from servicos import agenda, carrinho, db, formato, loja

DIAS_VISIVEIS = 14


def render() -> None:
    ui.aplicar_estilo()
    ui.cabecalho("Escolha o dia e o horário")

    itens = carrinho.carregar_carrinho()
    mapa = db.mapa_servicos()
    itens = {sid: q for sid, q in itens.items() if sid in mapa}

    if not itens:
        st.warning("Seu carrinho está vazio.")
        if st.button("Ver serviços", type="primary"):
            ui.ir_para(p=None)
        return

    porte_codigo = carrinho.carregar_porte()
    porte = db.buscar_porte(porte_codigo)
    acrescimo = int(porte["acrescimo_centavos"]) if porte else 0

    duracao = agenda.duracao_total(mapa, itens)
    total = agenda.total_centavos(mapa, itens) + acrescimo

    with st.container(border=True):
        st.markdown("<div class='lc-secao'>Seu pedido</div>", unsafe_allow_html=True)
        for sid, qtd in itens.items():
            s = mapa[sid]
            st.markdown(
                f"<p class='lc-nome'>{s['nome']}</p>"
                f"<span class='lc-meta'>{formato.duracao_humana(int(s['duracao_min']) * qtd)}"
                f" · {formato.reais(int(s['preco_centavos']) * qtd)}</span>",
                unsafe_allow_html=True)
        if acrescimo:
            st.markdown(
                f"<span class='lc-meta'>Acréscimo {porte['nome']} · "
                f"{formato.reais(acrescimo)}</span>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='lc-preco'>{formato.reais(total)}"
            f"<br><small>{porte['nome'] if porte else ''} · "
            f"{formato.duracao_humana(duracao)} de serviço</small></div>",
            unsafe_allow_html=True)

    if st.button("← Mudar serviço ou porte"):
        ui.ir_para(p=None)

    hoje = datetime.now(agenda.TZ).date()
    dia = st.date_input("Dia", value=st.session_state.get("dia", hoje),
                        min_value=hoje, max_value=hoje + timedelta(days=DIAS_VISIVEIS),
                        format="DD/MM/YYYY")
    st.session_state.dia = dia

    _grade(dia, duracao, mapa, itens, total, porte, acrescimo)


@st.fragment
def _grade(dia: date, duracao: int, mapa: dict, itens: dict, total: int,
           porte: dict | None, acrescimo: int) -> None:
    cfg = db.buscar_config(dia)
    if cfg is None or not cfg.aberto:
        st.info("Fechado neste dia. Escolha outra data.")
        return

    livres = agenda.horarios_livres(
        dia, duracao, cfg,
        db.buscar_ocupados(dia),
        db.buscar_bloqueios(dia),
    )

    st.caption(f"Aberto das {cfg.abre.strftime('%H:%M')} às "
               f"{cfg.fecha.strftime('%H:%M')} · {cfg.qtd_boxes} box(es)")

    if not livres:
        st.warning("Nenhum horário livre para essa duração neste dia. "
                   "Tente outra data ou escolha outro serviço.")
        return

    st.markdown("**Horários livres**")
    colunas = st.columns(4)
    for i, slot in enumerate(livres):
        if colunas[i % 4].button(slot.strftime("%H:%M"), key=f"slot{slot.isoformat()}",
                                 width="stretch"):
            st.session_state.slot_escolhido = slot.isoformat()
            ui.rerun_bloco()

    # O dialogo precisa ser reaberto a cada rerun enquanto o cliente
    # preenche os campos. Abrir dentro do `if` do botao nao funciona:
    # no rerun seguinte o botao ja e False e o clique em "Confirmar"
    # se perderia.
    if escolhido := st.session_state.get("slot_escolhido"):
        slot = datetime.fromisoformat(escolhido)
        if slot in livres:
            _checkout(slot, duracao, mapa, itens, total, cfg.qtd_boxes,
                      porte, acrescimo)
        else:
            st.session_state.pop("slot_escolhido", None)


@st.dialog("Seus dados")
def _checkout(slot: datetime, duracao: int, mapa: dict, itens: dict,
              total: int, qtd_boxes: int, porte: dict | None,
              acrescimo: int) -> None:
    st.markdown(f"**{slot.strftime('%d/%m às %H:%M')}** · "
                f"{formato.duracao_humana(duracao)} · {formato.reais(total)}")

    nome = st.text_input("Nome completo")
    telefone = st.text_input("WhatsApp", placeholder="(14) 99890-4665")
    placa = st.text_input("Placa (opcional)", placeholder="ABC1D23")
    modelo = st.text_input("Modelo do carro (opcional)", placeholder="Onix prata")

    confirmar, voltar = st.columns([2, 1])
    if voltar.button("Voltar", width="stretch"):
        st.session_state.pop("slot_escolhido", None)
        st.rerun()
    if not confirmar.button("Confirmar agendamento", type="primary", width="stretch"):
        return

    tel = formato.normalizar_telefone(telefone)
    pla = formato.normalizar_placa(placa)
    erros = []
    if len(nome.strip()) < 3:
        erros.append("Informe seu nome completo.")
    if not tel:
        erros.append("WhatsApp inválido. Use DDD + número.")
    # A placa e opcional; so reclama de placa preenchida em formato errado.
    if placa.strip() and not pla:
        erros.append("Placa inválida. Use ABC1234 ou ABC1D23, "
                     "ou deixe em branco.")
    if erros:
        for e in erros:
            st.error(e)
        return

    linhas = [{"servico_id": sid, "nome": mapa[sid]["nome"],
               "preco_centavos": int(mapa[sid]["preco_centavos"]),
               "duracao_min": int(mapa[sid]["duracao_min"])}
              for sid, qtd in itens.items() for _ in range(qtd)]
    if acrescimo and porte:
        # O acrescimo entra como item, com servico_id nulo. Assim o total
        # continua sendo a soma dos itens e o comprovante mostra de onde
        # veio a diferenca de preco.
        linhas.append({"servico_id": None,
                       "nome": f"Acréscimo {porte['nome']}",
                       "preco_centavos": acrescimo, "duracao_min": 0})

    try:
        codigo = db.criar_agendamento(
            nome=nome.strip(), telefone=tel, placa=pla, modelo=modelo.strip(),
            inicio=slot, duracao_min=duracao, itens=linhas,
            qtd_boxes=qtd_boxes, exige_pagamento=bool(loja.pix()),
            porte_codigo=porte["codigo"] if porte else None,
        )
    except db.SlotIndisponivel:
        # A tela valida para ser gentil, a constraint valida para estar correto.
        st.error("Esse horário acabou de ser preenchido. Escolha outro.")
        st.cache_data.clear()
        return

    carrinho.limpar()
    st.session_state.pop("slot_escolhido", None)
    st.query_params.clear()
    st.query_params["pedido"] = codigo
    st.rerun()
