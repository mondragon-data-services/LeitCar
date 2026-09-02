"""PIX estatico: BR Code EMV montado offline (secao 2.4 da ARQUITETURA).

Sem gateway, sem API, sem taxa. O dinheiro cai direto na conta.
A baixa e manual, feita pelo dono no admin.
"""
from __future__ import annotations

from decimal import Decimal


def crc16(payload: str) -> str:
    """CRC-16/CCITT-FALSE (init 0xFFFF, poli 0x1021), em hex maiusculo."""
    crc = 0xFFFF
    for byte in payload.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def campo(cid: str, valor: str) -> str:
    return f"{cid}{len(valor):02d}{valor}"


def _limpar(texto: str) -> str:
    """EMV nao gosta de acento. Troca por ASCII e corta o resto."""
    import unicodedata
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return "".join(c for c in sem_acento if c.isalnum() or c in " .-").strip()


def montar_brcode(chave: str, nome: str, cidade: str,
                  valor: Decimal, txid: str) -> str:
    """Gera o payload EMV do PIX estatico. Sem internet, sem gateway."""
    mai = campo("00", "br.gov.bcb.pix") + campo("01", chave)
    payload = (
        campo("00", "01")
        + campo("26", mai)
        + campo("52", "0000")
        + campo("53", "986")
        + campo("54", f"{Decimal(valor):.2f}")
        + campo("58", "BR")
        + campo("59", _limpar(nome)[:25] or "LAVA CAR")
        + campo("60", _limpar(cidade)[:15] or "SAO PAULO")
        + campo("62", campo("05", (txid or "***")[:25]))
    )
    return payload + "6304" + crc16(payload + "6304")


def valor_com_centavos_unicos(centavos: int, codigo: str) -> int:
    """Opcao 2 da secao 2.4: centavos derivados do codigo do pedido.

    LC7F3K de R$ 89,00 vira R$ 89,07. No extrato cada valor e unico,
    e o dono concilia em segundos. Nao confie no txid para isso.
    """
    base = centavos - (centavos % 100)
    sufixo = sum(ord(c) for c in codigo) % 99 + 1   # 01..99, nunca 00
    return base + sufixo


def qrcode_png(payload: str) -> bytes:
    """PNG do BR Code, para st.image."""
    import io
    import qrcode

    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
