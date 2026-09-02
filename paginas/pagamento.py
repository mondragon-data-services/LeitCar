"""QR do PIX estatico e botao "Ja paguei" (Fase 7).

Sem gateway e sem webhook: o cliente paga, avisa no WhatsApp e o dono
da baixa no admin. O valor com centavos unicos e o que torna a
conciliacao rapida no extrato.
"""
from __future__ import annotations

from decimal import Decimal

import streamlit as st

from servicos import formato, loja, pix


def valor_a_pagar(pedido: dict, cfg: dict) -> int:
    """Sinal fixo (ou o total, se menor), com centavos unicos por pedido."""
    total = int(pedido["total_centavos"])
    sinal = min(int(cfg["sinal_centavos"]), total) if cfg["sinal_centavos"] else total
    if cfg["centavos_unicos"]:
        sinal = pix.valor_com_centavos_unicos(sinal, pedido["codigo"])
    return sinal


def render(pedido: dict) -> None:
    cfg = loja.pix()
    if not cfg:
        return

    centavos = valor_a_pagar(pedido, cfg)
    payload = pix.montar_brcode(
        chave=cfg["chave"], nome=cfg["nome"], cidade=cfg["cidade"],
        valor=Decimal(centavos) / 100, txid=pedido["codigo"],
    )

    with st.container(border=True):
        st.markdown(f"### Pague o sinal de {formato.reais(centavos)}")
        st.caption("O restante você paga na entrega. Os centavos são únicos "
                   "deste pedido e servem para identificar seu pagamento.")

        try:
            st.image(pix.qrcode_png(payload), width=240)
        except Exception:
            st.info("Use o código copia e cola abaixo.")

        st.text_area("PIX copia e cola", payload, height=110)

        info = loja.info()
        msg = (f"Olá! Sou {pedido['cliente_nome']}, acabei de pagar o pedido "
               f"{pedido['codigo']} no valor de {formato.reais(centavos)}. "
               "Segue o comprovante.")
        url = f"https://wa.me/{formato.telefone_wa(info['telefone'])}?text={_quote(msg)}"
        st.link_button("Já paguei, enviar comprovante", url,
                       type="primary", width="stretch")

    if pedido.get("expira_em") is not None:
        st.caption("Seu horário fica reservado por 30 minutos. Depois disso "
                   "ele volta para a agenda automaticamente.")


def _quote(texto: str) -> str:
    from urllib.parse import quote
    return quote(texto)
