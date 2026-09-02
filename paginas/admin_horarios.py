"""Horario de funcionamento e bloqueios (Fase 5).

O banco guarda a regra (aqui) e os fatos (agendamentos). Disponibilidade
e sempre calculada, nunca armazenada.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st

from servicos import agenda, db

NOMES = {0: "Domingo", 1: "Segunda", 2: "Terça", 3: "Quarta",
         4: "Quinta", 5: "Sexta", 6: "Sábado"}


def render() -> None:
    st.title("Horários")

    linhas = db.listar_horarios()
    df = pd.DataFrame(linhas)
    if df.empty:
        df = pd.DataFrame([{"dia_semana": d, "abre": time(8, 0), "fecha": time(18, 0),
                            "qtd_boxes": 1, "aberto": d != 0} for d in range(7)])
    df["dia"] = df["dia_semana"].map(NOMES)
    df["abre"] = df["abre"].map(lambda v: v if isinstance(v, time) else time.fromisoformat(str(v)))
    df["fecha"] = df["fecha"].map(lambda v: v if isinstance(v, time) else time.fromisoformat(str(v)))

    editado = st.data_editor(
        df[["dia_semana", "dia", "abre", "fecha", "qtd_boxes", "aberto"]],
        width="stretch", hide_index=True, num_rows="fixed",
        column_config={
            "dia_semana": None,
            "dia": st.column_config.TextColumn("Dia", disabled=True),
            "abre": st.column_config.TimeColumn("Abre", format="HH:mm", step=900),
            "fecha": st.column_config.TimeColumn("Fecha", format="HH:mm", step=900),
            "qtd_boxes": st.column_config.NumberColumn("Boxes", min_value=1, max_value=20,
                                                       step=1),
            "aberto": st.column_config.CheckboxColumn("Aberto"),
        },
        key="editor_horarios",
    )

    if st.button("Salvar horários", type="primary"):
        db.salvar_horarios(editado.to_dict("records"))
        st.success("Horários salvos.")
        st.rerun()

    st.divider()
    st.subheader("Bloqueios")
    st.caption("Feriado, manutenção, folga. Horários dentro do período somem da agenda.")

    with st.form("novo_bloqueio"):
        c1, c2, c3 = st.columns(3)
        dia = c1.date_input("Dia", value=datetime.now(agenda.TZ).date(),
                            format="DD/MM/YYYY")
        h_ini = c2.time_input("Das", value=time(8, 0), step=900)
        h_fim = c3.time_input("Até", value=time(18, 0), step=900)
        motivo = st.text_input("Motivo", placeholder="Feriado")
        if st.form_submit_button("Bloquear", type="primary"):
            inicio = datetime.combine(dia, h_ini, tzinfo=agenda.TZ)
            fim = datetime.combine(dia, h_fim, tzinfo=agenda.TZ)
            if fim <= inicio:
                fim += timedelta(days=1)
            db.criar_bloqueio(inicio, fim, motivo or "")
            st.rerun()

    for b in db.listar_bloqueios():
        ini = b["inicio"].astimezone(agenda.TZ)
        fim = b["fim"].astimezone(agenda.TZ)
        col1, col2 = st.columns([4, 1], vertical_alignment="center")
        col1.write(f"{ini.strftime('%d/%m %H:%M')} → {fim.strftime('%d/%m %H:%M')}"
                   f" — {b['motivo'] or 'sem motivo'}")
        if col2.button("Remover", key=f"bl{b['id']}", width="stretch"):
            db.remover_bloqueio(int(b["id"]))
            st.rerun()
