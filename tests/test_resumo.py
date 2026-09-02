"""Agrupamento por período do acompanhamento.

O gráfico depende de duas coisas que já quebraram: a ordem cronológica
dos baldes e a presença dos períodos vazios. Sem os vazios, duas semanas
movimentadas encostam uma na outra e o gráfico mente sobre o ritmo.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from paginas.admin_resumo import (AGENDADO, CONCLUIDO, MESES, _balde, _rotulo,
                                  serie_por_periodo)
from servicos.agenda import TZ


def em(ano: int, mes: int, dia: int) -> datetime:
    return datetime(ano, mes, dia, 9, 0, tzinfo=TZ)


def registro(quando: datetime, status: str) -> dict:
    return {"inicio": quando, "status": status, "total_centavos": 8000,
            "servicos": "Lavagem simples", "codigo": "LC1", "porte_codigo": "carro"}


def test_semana_comeca_na_segunda():
    # 2026-09-02 e uma quarta; a semana dela comeca em 31/08 (segunda)
    assert _balde(date(2026, 9, 2), "semana") == date(2026, 8, 31)
    assert _balde(date(2026, 8, 31), "semana") == date(2026, 8, 31)
    assert _balde(date(2026, 9, 6), "semana") == date(2026, 8, 31)   # domingo
    assert _balde(date(2026, 9, 7), "semana") == date(2026, 9, 7)


def test_mes_agrupa_no_dia_primeiro():
    assert _balde(date(2026, 9, 23), "mês") == date(2026, 9, 1)


def test_rotulo_de_mes_sai_em_portugues():
    """strftime('%b') devolveria 'Sep': o locale pt_BR nao esta garantido."""
    assert _rotulo(date(2026, 9, 1), "mês") == "set/26"
    assert _rotulo(date(2026, 1, 1), "mês") == "jan/26"
    assert len(MESES) == 12
    assert _rotulo(date(2026, 9, 2), "semana") == "02/09"


def test_periodos_vazios_entram_com_zero():
    linhas = [registro(em(2026, 8, 3), "concluido"),
              registro(em(2026, 8, 24), "concluido")]
    df = serie_por_periodo(linhas, date(2026, 8, 3), date(2026, 8, 30), "semana")

    assert len(df) == 4                       # 03/08, 10/08, 17/08, 24/08
    assert list(df["Período"]) == ["03/08", "10/08", "17/08", "24/08"]
    assert list(df[CONCLUIDO]) == [1, 0, 0, 1]


def test_ordem_e_cronologica_atravessando_a_virada_do_mes():
    """Ordenado como texto, '03/08' cairia depois de '28/09'."""
    df = serie_por_periodo([], date(2026, 8, 3), date(2026, 9, 28), "semana")
    assert list(df["Período"])[:2] == ["03/08", "10/08"]
    assert list(df["Período"])[-1] == "28/09"


def test_separa_concluidos_de_agendados():
    linhas = [registro(em(2026, 9, 1), "concluido"),
              registro(em(2026, 9, 2), "confirmado"),
              registro(em(2026, 9, 3), "pendente")]
    df = serie_por_periodo(linhas, date(2026, 8, 31), date(2026, 9, 6), "semana")
    assert df[CONCLUIDO].sum() == 1
    assert df[AGENDADO].sum() == 2            # confirmado e pendente contam juntos


def test_cancelado_e_expirado_ficam_fora_do_grafico():
    linhas = [registro(em(2026, 9, 1), "cancelado"),
              registro(em(2026, 9, 2), "expirado"),
              registro(em(2026, 9, 3), "concluido")]
    df = serie_por_periodo(linhas, date(2026, 8, 31), date(2026, 9, 6), "semana")
    assert df[CONCLUIDO].sum() == 1
    assert df[AGENDADO].sum() == 0


def test_registro_fora_da_janela_e_ignorado():
    linhas = [registro(em(2026, 7, 1), "concluido")]
    df = serie_por_periodo(linhas, date(2026, 8, 31), date(2026, 9, 6), "semana")
    assert df[CONCLUIDO].sum() == 0


def test_doze_meses_geram_treze_baldes():
    inicio = date(2026, 9, 2) - timedelta(days=364)
    df = serie_por_periodo([], inicio, date(2026, 9, 16), "mês")
    assert len(df) == 13
    assert df["Período"].iloc[0] == "set/25"
    assert df["Período"].iloc[-1] == "set/26"
