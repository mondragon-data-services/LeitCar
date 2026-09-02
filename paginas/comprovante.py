"""?pedido=LC7F3K (secao 2.6 da ARQUITETURA).

Nao existe rota /pedido/LC7F3K, mas o query param faz o mesmo papel:
e linkavel, sobrevive a refresh e cabe no WhatsApp.
"""
from __future__ import annotations

from urllib.parse import quote

import streamlit as st

from paginas import pagamento, ui
from servicos import agenda, db, formato, loja


def render(codigo: str) -> None:
    ui.aplicar_estilo()
    ui.cabecalho("Seu agendamento")

    pedido = db.buscar_agendamento(codigo)
    if not pedido:
        st.error(f"Pedido {codigo} não encontrado.")
        if st.button("Voltar para o início"):
            st.query_params.clear()
            st.rerun()
        return

    inicio = pedido["inicio"].astimezone(agenda.TZ)
    fim = pedido["fim"].astimezone(agenda.TZ)
    status = pedido["status"]

    with st.container(border=True):
        st.markdown(f"## {pedido['codigo']} {ui.chip_status(status)}",
                    unsafe_allow_html=True)
        # Placa e modelo sao opcionais: so entram na linha se vierem preenchidos.
        detalhes = " · ".join(p for p in (
            f"Box {pedido['box']}",
            formato.placa_humana(pedido["veiculo_placa"] or ""),
            pedido["veiculo_modelo"] or "") if p)
        st.markdown(
            f"**{inicio.strftime('%d/%m/%Y')} das {inicio.strftime('%H:%M')} "
            f"às {fim.strftime('%H:%M')}**  \n"
            f"<span class='lc-meta'>{detalhes}</span>",
            unsafe_allow_html=True)

        st.divider()
        for it in pedido["itens"]:
            st.markdown(
                f"<span class='lc-meta'>{it['nome_snapshot']} · "
                f"{formato.duracao_humana(int(it['duracao_min']))} · "
                f"{formato.reais(int(it['preco_centavos']))}</span>",
                unsafe_allow_html=True)
        st.markdown(f"<span class='lc-preco'>Total "
                    f"{formato.reais(int(pedido['total_centavos']))}</span>",
                    unsafe_allow_html=True)

    if status == "pendente" and loja.pix():
        pagamento.render(pedido)
    elif status == "confirmado":
        st.success("Agendamento confirmado. Pagamento na entrega.")
    elif status == "concluido":
        st.info("Serviço concluído. Obrigado!")
    elif status in ("cancelado", "expirado"):
        st.error("Este agendamento não está mais ativo.")

    info = loja.info()
    link = f"{info['url_publica']}/?pedido={pedido['codigo']}"
    msg = f"Meu agendamento no {info['nome']}: {pedido['codigo']} - {link}"
    esq, dir_ = st.columns(2)
    esq.link_button("Falar no WhatsApp",
                    f"https://wa.me/{formato.telefone_wa(info['telefone'])}?text={quote(msg)}",
                    width="stretch")
    if dir_.button("Agendar outro", width="stretch"):
        st.query_params.clear()
        st.rerun()

    st.caption(f"Guarde este link: `{link}`")

    if status in ("pendente", "confirmado"):
        with st.expander("Preciso cancelar"):
            st.caption("O horário volta para a agenda na hora.")
            if st.button("Cancelar agendamento"):
                db.mudar_status(pedido["codigo"], "cancelado")
                st.rerun()
