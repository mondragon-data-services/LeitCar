"""BR Code EMV comparado com um payload conhecido (secao 11, Fase 7)."""
from __future__ import annotations

from decimal import Decimal

from servicos.formato import normalizar_placa, normalizar_telefone, reais
from servicos.pix import crc16, montar_brcode, valor_com_centavos_unicos

def ler_tlv(payload: str) -> dict[str, str]:
    """Parser EMV: id(2) + tamanho(2) + valor. Serve para conferir o payload."""
    campos, i = {}, 0
    while i < len(payload):
        cid = payload[i:i + 2]
        tamanho = int(payload[i + 2:i + 4])
        campos[cid] = payload[i + 4:i + 4 + tamanho]
        i += 4 + tamanho
    return campos


def test_crc16_bate_com_o_vetor_oficial():
    """Vetor de verificacao do CRC-16/CCITT-FALSE: "123456789" -> 0x29B1."""
    assert crc16("123456789") == "29B1"


def test_brcode_tem_estrutura_emv_e_crc_valido():
    payload = montar_brcode(chave="lavacar@exemplo.com.br", nome="Lava Car Online",
                            cidade="Sao Paulo", valor=Decimal("89.07"), txid="LC7F3K")
    campos = ler_tlv(payload)
    assert campos["00"] == "01"                      # payload format indicator
    assert campos["52"] == "0000"                    # merchant category code
    assert campos["53"] == "986"                     # moeda: BRL
    assert campos["54"] == "89.07"                   # valor com 2 casas
    assert campos["58"] == "BR"
    assert campos["59"] == "Lava Car Online"
    assert campos["60"] == "Sao Paulo"
    assert ler_tlv(campos["26"]) == {"00": "br.gov.bcb.pix",
                                     "01": "lavacar@exemplo.com.br"}
    assert ler_tlv(campos["62"]) == {"05": "LC7F3K"}
    # O CRC fecha sobre o proprio payload, incluindo o "6304" do campo 63.
    assert campos["63"] == crc16(payload[:-4])


def test_acento_do_recebedor_nao_entra_no_payload():
    payload = montar_brcode(chave="k", nome="Lavação Água Viva", cidade="São Paulo",
                            valor=Decimal("20.00"), txid="LC1")
    assert "Lavacao Agua Viva" in payload
    assert "Sao Paulo" in payload


def test_centavos_unicos_identificam_o_pedido():
    a = valor_com_centavos_unicos(8900, "LC7F3K")
    b = valor_com_centavos_unicos(8900, "LC7F3L")
    assert a != b
    assert a % 100 != 0                  # nunca cai em centavos zerados
    assert 8900 <= a < 9000


def test_formatacao_brasileira():
    assert reais(3500) == "R$ 35,00"
    assert reais(124900) == "R$ 1.249,00"
    assert normalizar_telefone("+55 (11) 99999-0000") == "11999990000"
    assert normalizar_telefone("123") == ""
    assert normalizar_placa("abc-1d23") == "ABC1D23"
    assert normalizar_placa("ABC1234") == "ABC1234"
    assert normalizar_placa("AB123") == ""
