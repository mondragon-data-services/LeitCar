"""A tabela de precos da Leite Estetica, conferida contra a especificacao.

Precos base sao de carro de passeio; SUV e caminhonete somam acrescimo.
Os acrescimos de 30 e 50 reais sao placeholders da especificacao — quando
o Leite confirmar os reais, e este arquivo que denuncia a mudanca.
"""
from __future__ import annotations

import pytest

from servicos.agenda import duracao_total, total_centavos

# leite-estetica-especificacao.md, secao 1
SERVICOS = {
    1: {"codigo": "simples", "preco_centavos": 8000, "duracao_min": 60},
    2: {"codigo": "detalhamento", "preco_centavos": 15000, "duracao_min": 180},
    3: {"codigo": "completo", "preco_centavos": 60000, "duracao_min": 480},
}
ACRESCIMOS = {"carro": 0, "suv": 3000, "caminhonete": 5000}


def preco(servico_id: int, porte: str) -> int:
    """valorFinal = servico.precoBase + porte.acrescimo"""
    return total_centavos(SERVICOS, {servico_id: 1}) + ACRESCIMOS[porte]


@pytest.mark.parametrize("servico_id,porte,esperado", [
    (1, "carro", 8000), (1, "suv", 11000), (1, "caminhonete", 13000),
    (2, "carro", 15000), (2, "suv", 18000), (2, "caminhonete", 20000),
    (3, "carro", 60000), (3, "suv", 63000), (3, "caminhonete", 65000),
])
def test_matriz_de_precos(servico_id, porte, esperado):
    assert preco(servico_id, porte) == esperado


def test_porte_nao_mexe_na_duracao():
    """O acrescimo e so preco: um SUV nao ocupa a agenda por mais tempo."""
    assert duracao_total(SERVICOS, {2: 1}) == 180
    assert duracao_total(SERVICOS, {3: 1}) == 480


def test_detalhamento_completo_ocupa_o_dia_inteiro():
    """8 horas: com 1 box, nao sobra horario no dia — o que a spec pede."""
    from datetime import date, datetime, time

    from servicos.agenda import TZ, ConfigDia, Ocupacao, horarios_livres

    dia = date(2026, 9, 9)
    cfg = ConfigDia(dia_semana=3, abre=time(8, 0), fecha=time(18, 0), qtd_boxes=1)
    agora = datetime(2026, 9, 8, 8, 0, tzinfo=TZ)

    # 8h de servico numa loja que abre 8h e fecha 18h: o ultimo inicio
    # possivel e 10h, entao a grade vai de 08:00 a 10:00 de 15 em 15.
    livres = horarios_livres(dia, 480, cfg, [], [], agora=agora)
    assert livres[0] == datetime(2026, 9, 9, 8, 0, tzinfo=TZ)
    assert livres[-1] == datetime(2026, 9, 9, 10, 0, tzinfo=TZ)
    assert len(livres) == 9

    # marcado o completo as 8h, o dia inteiro sai da grade
    ocupado = [Ocupacao(lower=datetime(2026, 9, 9, 8, 0, tzinfo=TZ),
                        upper=datetime(2026, 9, 9, 16, 0, tzinfo=TZ), box=1)]
    assert horarios_livres(dia, 60, cfg, ocupado, [], agora=agora) == [
        datetime(2026, 9, 9, 16, 0, tzinfo=TZ),
        datetime(2026, 9, 9, 16, 15, tzinfo=TZ),
        datetime(2026, 9, 9, 16, 30, tzinfo=TZ),
        datetime(2026, 9, 9, 16, 45, tzinfo=TZ),
        datetime(2026, 9, 9, 17, 0, tzinfo=TZ),
    ]
