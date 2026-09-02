"""Teste 3 da secao 12: dois inserts no mesmo box e horario levantam IntegrityError.

Este e o unico teste que precisa de banco. Roda quando DATABASE_URL esta
definida (docker compose run --rm testes), e e pulado fora disso.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from servicos.agenda import TZ

URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="sem DATABASE_URL")

INSERT = text("""
    insert into agendamentos
      (codigo, cliente_nome, cliente_telefone, veiculo_placa, box, periodo,
       total_centavos, status, expira_em)
    values
      (:codigo, 'Teste', '11999990000', 'ABC1D23', :box,
       tstzrange(:ini, :fim, '[)'), 1000, :status, :expira)
""")


@pytest.fixture
def conn():
    eng = create_engine(URL)
    with eng.begin() as c:
        c.execute(text("delete from agendamentos where cliente_nome = 'Teste'"))
    with eng.connect() as c:
        yield c
    with eng.begin() as c:
        c.execute(text("delete from agendamentos where cliente_nome = 'Teste'"))


def _slot(dias: int = 30):
    ini = (datetime.now(TZ) + timedelta(days=dias)).replace(
        hour=9, minute=0, second=0, microsecond=0)
    return ini, ini + timedelta(minutes=60)


def test_mesmo_box_no_mesmo_horario_levanta_integrity_error(conn):
    ini, fim = _slot()
    conn.execute(INSERT, {"codigo": "TST001", "box": 1, "ini": ini, "fim": fim,
                          "status": "confirmado", "expira": None})
    conn.commit()

    with pytest.raises(IntegrityError) as erro:
        conn.execute(INSERT, {"codigo": "TST002", "box": 1, "ini": ini, "fim": fim,
                              "status": "confirmado", "expira": None})
        conn.commit()
    assert "sem_overbooking" in str(erro.value)
    conn.rollback()


def test_box_diferente_no_mesmo_horario_passa(conn):
    ini, fim = _slot(31)
    conn.execute(INSERT, {"codigo": "TST003", "box": 1, "ini": ini, "fim": fim,
                          "status": "confirmado", "expira": None})
    conn.execute(INSERT, {"codigo": "TST004", "box": 2, "ini": ini, "fim": fim,
                          "status": "confirmado", "expira": None})
    conn.commit()
    total = conn.execute(text(
        "select count(*) from agendamentos where cliente_nome = 'Teste'")).scalar_one()
    assert total == 2


def test_cancelado_libera_o_box(conn):
    ini, fim = _slot(32)
    conn.execute(INSERT, {"codigo": "TST005", "box": 1, "ini": ini, "fim": fim,
                          "status": "cancelado", "expira": None})
    conn.execute(INSERT, {"codigo": "TST006", "box": 1, "ini": ini, "fim": fim,
                          "status": "confirmado", "expira": None})
    conn.commit()
