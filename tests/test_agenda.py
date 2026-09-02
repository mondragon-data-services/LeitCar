"""Os quatro testes da secao 12, sem envolver o Streamlit."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta

from servicos.agenda import (TZ, ConfigDia, Intervalo, Ocupacao, dia_semana_bd,
                             duracao_total, escolher_box, horarios_livres,
                             ocupacoes_vigentes)

DIA = date(2026, 9, 9)                       # quarta-feira
AGORA_CEDO = datetime(2026, 9, 9, 6, 0, tzinfo=TZ)   # "agora" fixo, longe do expediente
CFG = ConfigDia(dia_semana=3, abre=time(8, 0), fecha=time(18, 0), qtd_boxes=2)


def em(hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 9, 9, hora, minuto, tzinfo=TZ)


def test_slot_que_ultrapassa_o_fechamento_nao_aparece():
    """Loja fecha as 18h; com 90 min o ultimo slot possivel e 16:30."""
    livres = horarios_livres(DIA, 90, CFG, [], [], agora=AGORA_CEDO)
    assert livres[-1] == em(16, 30)
    assert em(17, 0) not in livres


def test_dois_boxes_ocupados_somem_o_slot():
    """Exemplo concreto da secao 6: 9h-10h30 no box 1, 9h30-10h no box 2."""
    ocupados = [
        Ocupacao(lower=em(9, 0), upper=em(10, 30), box=1),
        Ocupacao(lower=em(9, 30), upper=em(10, 0), box=2),
    ]
    livres = horarios_livres(DIA, 90, CFG, ocupados, [], agora=AGORA_CEDO)

    assert em(9, 30) not in livres          # os 2 boxes estao ocupados
    assert em(10, 30) in livres             # box 1 e 2 livres a partir dai
    assert em(8, 0) in livres               # box 1 ocupado, mas o box 2 so comeca 9h30
    assert em(10, 0) in livres              # colide so com o box 1; sobra o box 2


def test_bloqueio_remove_o_slot():
    bloqueios = [Intervalo(lower=em(13, 0), upper=em(14, 0))]
    livres = horarios_livres(DIA, 30, CFG, [], bloqueios, agora=AGORA_CEDO)
    assert em(13, 0) not in livres
    assert em(12, 30) in livres             # termina exatamente as 13h, nao invade
    assert em(14, 0) in livres


def test_pendente_vencido_deixa_de_ocupar_o_slot():
    agora = em(9, 0)
    linhas = [
        {"lower": em(14, 0), "upper": em(15, 0), "box": 1,
         "status": "pendente", "expira_em": em(8, 30)},          # vencido
        {"lower": em(14, 0), "upper": em(15, 0), "box": 2,
         "status": "pendente", "expira_em": em(9, 30)},          # ainda vale
        {"lower": em(16, 0), "upper": em(17, 0), "box": 1,
         "status": "cancelado", "expira_em": None},
    ]
    vivos = ocupacoes_vigentes(linhas, agora=agora)
    assert len(vivos) == 1
    assert vivos[0].box == 2

    livres = horarios_livres(DIA, 60, CFG, vivos, [], agora=em(6, 0))
    assert em(14, 0) in livres              # sobrou o box 1


def test_antecedencia_minima_corta_os_slots_de_hoje():
    agora = em(9, 5)                        # antecedencia padrao: 60 min
    livres = horarios_livres(DIA, 30, CFG, [], [], agora=agora)
    assert livres[0] == em(10, 15)


def test_dia_fechado_nao_tem_slot():
    fechado = ConfigDia(dia_semana=0, abre=time(8, 0), fecha=time(12, 0),
                        qtd_boxes=2, aberto=False)
    assert horarios_livres(DIA, 30, fechado, [], [], agora=AGORA_CEDO) == []
    assert horarios_livres(DIA, 30, None, [], [], agora=AGORA_CEDO) == []


def test_escolher_box_devolve_o_primeiro_livre():
    ocupados = [Ocupacao(lower=em(9, 0), upper=em(10, 0), box=1)]
    assert escolher_box(em(9, 0), em(10, 0), ocupados, [], 2) == 2
    assert escolher_box(em(9, 0), em(10, 0), ocupados, [], 1) is None
    assert escolher_box(em(10, 0), em(11, 0), ocupados, [], 2) == 1


def test_dia_semana_bd_usa_domingo_zero():
    assert dia_semana_bd(date(2026, 9, 6)) == 0     # domingo
    assert dia_semana_bd(date(2026, 9, 7)) == 1     # segunda
    assert dia_semana_bd(date(2026, 9, 12)) == 6    # sabado


def test_duracao_total_multiplica_pela_quantidade():
    servicos = {1: {"duracao_min": 60, "preco_centavos": 6900},
                2: {"duracao_min": 30, "preco_centavos": 4000}}
    assert duracao_total(servicos, {1: 1, 2: 1}) == 90
    assert duracao_total(servicos, {2: 3}) == 90
