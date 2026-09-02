"""Agenda do dia e baixa manual dos pagamentos (Fase 5)."""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import quote

import pandas as pd
import streamlit as st

from paginas import ui
from servicos import agenda, db, formato, loja


def _link_pronto(r: dict) -> str:
    """Link do WhatsApp com a mensagem de carro pronto ja escrita.

    Usa o telefone que o proprio cliente informou no agendamento, entao
    o dono nao precisa procurar o contato nem copiar numero.
    """
    info = loja.info()
    veiculo = (formato.placa_humana(r["veiculo_placa"] or "")
               or r["veiculo_modelo"] or "").strip()
    seu_carro = f"Seu {veiculo}" if veiculo else "Seu carro"
    msg = (f"Olá, {r['cliente_nome'].split()[0]}! Aqui é da {info['nome']}. "
           f"{seu_carro} está pronto e pode ser retirado. "
           f"Total: {formato.reais(int(r['total_centavos']))}. "
           f"Pedido {r['codigo']}. Obrigado pela preferência!")
    return (f"https://wa.me/{formato.telefone_wa(r['cliente_telefone'])}"
            f"?text={quote(msg)}")


def render() -> None:
    st.title("Agenda")

    hoje = datetime.now(agenda.TZ).date()
    esq, dir_ = st.columns([2, 1], vertical_alignment="bottom")
    dia = esq.date_input("Dia", value=hoje, format="DD/MM/YYYY")
    if dir_.button("Atualizar", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    db.expirar_pendentes()
    linhas = db.agendamentos_do_dia(dia)
    ativos = [r for r in linhas if r["status"] not in ("cancelado", "expirado")]

    a, b, c = st.columns(3)
    a.metric("Agendamentos", len(ativos))
    b.metric("Faturamento previsto",
             formato.reais(sum(int(r["total_centavos"]) for r in ativos)))
    c.metric("Aguardando pagamento",
             sum(1 for r in ativos if r["status"] == "pendente"))

    if not linhas:
        st.info("Nenhum agendamento neste dia.")
    else:
        st.dataframe(
            pd.DataFrame([{
                "Hora": r["inicio"].astimezone(agenda.TZ).strftime("%H:%M"),
                "Fim": r["fim"].astimezone(agenda.TZ).strftime("%H:%M"),
                "Box": r["box"],
                "Código": r["codigo"],
                "Cliente": r["cliente_nome"],
                "Telefone": formato.telefone_humano(r["cliente_telefone"]),
                "Placa": formato.placa_humana(r["veiculo_placa"] or ""),
                "Veículo": r["veiculo_modelo"] or "",
                "Total": formato.reais(int(r["total_centavos"])),
                "Status": ui.ROTULOS_STATUS.get(r["status"], r["status"]),
            } for r in linhas]),
            width="stretch", hide_index=True,
        )

    st.subheader("Ações")
    for r in linhas:
        if r["status"] in ("cancelado", "expirado"):
            continue
        with st.container(border=True):
            info, acoes = st.columns([3, 2], vertical_alignment="center")
            veiculo = " · ".join(p for p in (
                formato.placa_humana(r["veiculo_placa"] or ""),
                r["veiculo_modelo"] or "") if p) or "veículo não informado"
            info.markdown(
                f"**{r['inicio'].astimezone(agenda.TZ).strftime('%H:%M')} · "
                f"{r['codigo']}** — {r['cliente_nome']} "
                f"({veiculo}) · "
                f"{formato.reais(int(r['total_centavos']))} · "
                f"`{ui.ROTULOS_STATUS.get(r['status'], r['status'])}`")
            with acoes:
                col1, col2, col3 = st.columns(3)
                if r["status"] == "pendente" and col1.button(
                        "Pago", key=f"pg{r['id']}", width="stretch",
                        help="Dar baixa: confirma o pagamento manualmente"):
                    db.mudar_status(r["codigo"], "confirmado")
                    st.rerun()
                if r["status"] == "confirmado" and col2.button(
                        "Concluir", key=f"cl{r['id']}", width="stretch"):
                    db.mudar_status(r["codigo"], "concluido")
                    st.rerun()
                if r["status"] == "concluido":
                    col2.link_button("Avisar", _link_pronto(r), width="stretch",
                                     type="primary",
                                     help="Abre o WhatsApp do cliente com a "
                                          "mensagem de carro pronto")
                if col3.button("Cancelar", key=f"cx{r['id']}", width="stretch"):
                    db.mudar_status(r["codigo"], "cancelado")
                    st.rerun()

    with st.expander("Próximos dias"):
        for i in range(1, 8):
            d = dia + timedelta(days=i)
            qtd = len([r for r in db.agendamentos_do_dia(d)
                       if r["status"] not in ("cancelado", "expirado")])
            st.write(f"{d.strftime('%d/%m (%a)')}: {qtd} agendamento(s)")
