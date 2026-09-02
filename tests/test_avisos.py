"""Aviso de carro pronto no WhatsApp, disparado pelo admin.

O telefone usado e o que o proprio cliente digitou no agendamento, entao
o dono nao precisa procurar contato nem copiar numero na mao.
"""
from __future__ import annotations

from urllib.parse import unquote

from paginas.admin_agenda import _link_pronto


def pedido(**extra) -> dict:
    base = {"codigo": "LC7F3K", "cliente_nome": "Maria Souza Lima",
            "cliente_telefone": "14988887777", "veiculo_placa": "ABC1D23",
            "veiculo_modelo": "Gol branco", "total_centavos": 8000}
    return {**base, **extra}


def texto(url: str) -> str:
    return unquote(url.split("text=")[1])


def test_link_usa_o_telefone_do_cadastro_com_ddi():
    url = _link_pronto(pedido())
    assert url.startswith("https://wa.me/5514988887777?text=")


def test_mensagem_traz_primeiro_nome_veiculo_total_e_codigo():
    msg = texto(_link_pronto(pedido()))
    assert msg.startswith("Olá, Maria!")      # so o primeiro nome
    assert "ABC-1D23" in msg
    assert "R$ 80,00" in msg
    assert "LC7F3K" in msg


def test_sem_placa_cai_para_o_modelo():
    msg = texto(_link_pronto(pedido(veiculo_placa="")))
    assert "Seu Gol branco está pronto" in msg


def test_sem_placa_e_sem_modelo_a_mensagem_continua_natural():
    """Placa e modelo sao opcionais: a frase nao pode ficar capenga."""
    msg = texto(_link_pronto(pedido(veiculo_placa="", veiculo_modelo="")))
    assert "Seu carro está pronto" in msg
    assert "  " not in msg
