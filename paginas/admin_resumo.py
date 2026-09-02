"""Acompanhamento: o que já foi feito e o que vem pela frente.

Duas séries por período — concluídos e agendados — porque a pergunta do
dono é sempre a mesma: o movimento está subindo ou caindo? Cancelados
ficam fora do gráfico e aparecem só na contagem, para não disputarem a
leitura com o que interessa.

A janela sempre passa de hoje: concluído é passado, agendado é futuro, e
um gráfico que parasse em hoje mostraria só metade da história.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from servicos import agenda, db, formato

# Slots 1 e 2 do tema categórico, validados para as duas superfícies.
CORES = {"claro": ["#2a78d6", "#eb6834"], "escuro": ["#3987e5", "#d95926"]}
CONCLUIDO, AGENDADO = "Concluídos", "Agendados"
DIAS_A_FRENTE = 14

# Poucos baldes e gordos: 30 barras de 3px não se leem nem se acertam
# com o dedo. Semana resolve o mês e o trimestre; mês resolve o ano.
JANELAS = {
    "Últimos 30 dias": (30, "semana"),
    "Últimos 90 dias": (90, "semana"),
    "Últimos 12 meses": (365, "mês"),
}


def _cores() -> list[str]:
    """O tema do leitor escolhe os passos da paleta; não é flip automático."""
    try:
        escuro = st.context.theme.type == "dark"
    except Exception:
        escuro = False
    return CORES["escuro" if escuro else "claro"]


def _balde(d: date, agrupamento: str) -> date:
    """Primeiro dia do período a que a data pertence."""
    if agrupamento == "semana":
        return d - timedelta(days=d.weekday())
    return d.replace(day=1)


# strftime("%b") sai em ingles: o locale pt_BR nao vem instalado no
# container nem esta garantido no servidor. Tabela resolve e nao depende
# de configuracao de sistema nenhuma.
MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]


def _rotulo(d: date, agrupamento: str) -> str:
    if agrupamento == "semana":
        return d.strftime("%d/%m")
    return f"{MESES[d.month - 1]}/{d:%y}"


def _proximo(d: date, agrupamento: str) -> date:
    if agrupamento == "semana":
        return d + timedelta(days=7)
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def render() -> None:
    st.title("Acompanhamento")

    escolha = st.segmented_control(
        "Período", list(JANELAS), default="Últimos 30 dias",
        key="janela_resumo") or "Últimos 30 dias"
    dias, agrupamento = JANELAS[escolha]

    hoje = datetime.now(agenda.TZ).date()
    inicio = hoje - timedelta(days=dias - 1)
    fim = hoje + timedelta(days=DIAS_A_FRENTE)
    linhas = db.resumo_periodo(inicio, fim)

    _placar(linhas, hoje)
    st.divider()
    _grafico(linhas, inicio, fim, agrupamento)
    _por_servico(linhas)


def _placar(linhas: list[dict], hoje: date) -> None:
    concluidos = [r for r in linhas if r["status"] == "concluido"]
    agendados = [r for r in linhas
                 if r["status"] in ("confirmado", "pendente")
                 and r["inicio"].date() >= hoje]
    perdidos = [r for r in linhas if r["status"] in ("cancelado", "expirado")]
    faturado = sum(int(r["total_centavos"]) for r in concluidos)
    a_receber = sum(int(r["total_centavos"]) for r in agendados)

    # Duas linhas de dois: em quatro colunas o valor em reais é truncado.
    a, b = st.columns(2)
    a.metric("Serviços concluídos", len(concluidos))
    b.metric("Faturamento realizado", formato.reais(faturado))
    c, d = st.columns(2)
    c.metric("Na agenda", len(agendados),
             help="Confirmados ou aguardando pagamento, de hoje em diante")
    d.metric("A receber", formato.reais(a_receber),
             help="Soma do que está marcado e ainda não foi entregue")

    if concluidos:
        st.caption(f"Ticket médio dos concluídos: "
                   f"**{formato.reais(faturado // len(concluidos))}**"
                   + (f" · {len(perdidos)} cancelado(s) ou expirado(s) no período,"
                      " fora do gráfico" if perdidos else ""))


def serie_por_periodo(linhas: list[dict], inicio: date, fim: date,
                      agrupamento: str) -> pd.DataFrame:
    """Uma linha por período, com as duas contagens lado a lado.

    Períodos vazios entram com zero: sem isso o gráfico mente, encostando
    duas semanas movimentadas como se fossem seguidas.
    """
    baldes: dict[date, dict[str, int]] = {}
    atual = _balde(inicio, agrupamento)
    limite = _balde(fim, agrupamento)
    while atual <= limite:
        baldes[atual] = {CONCLUIDO: 0, AGENDADO: 0}
        atual = _proximo(atual, agrupamento)

    for r in linhas:
        if r["status"] in ("cancelado", "expirado"):
            continue
        chave = _balde(r["inicio"].date(), agrupamento)
        if chave not in baldes:
            continue
        serie = CONCLUIDO if r["status"] == "concluido" else AGENDADO
        baldes[chave][serie] += 1

    return pd.DataFrame([
        {"Período": _rotulo(k, agrupamento), **v}
        for k, v in sorted(baldes.items())
    ])


def _grafico(linhas: list[dict], inicio: date, fim: date, agrupamento: str) -> None:
    st.subheader("Serviços por período")
    st.caption(f"Uma barra por {agrupamento}. Concluídos são o que já foi "
               f"entregue; agendados, o que está marcado — inclusive os "
               f"próximos {DIAS_A_FRENTE} dias.")

    df = serie_por_periodo(linhas, inicio, fim, agrupamento)
    if int(df[[CONCLUIDO, AGENDADO]].to_numpy().sum()) == 0:
        st.info("Nenhum serviço no período. O gráfico aparece assim que o "
                "primeiro agendamento entrar.")
        return

    # sort=False mantém a ordem cronológica das linhas: os rótulos são
    # texto, e ordenados sozinhos "04/08" cairia depois de "30/09".
    st.bar_chart(df, x="Período", y=[CONCLUIDO, AGENDADO], color=_cores(),
                 stack=False, sort=False, x_label="", y_label="serviços",
                 height=340)

    with st.expander("Ver os números"):
        st.dataframe(df, width="stretch", hide_index=True)


def _por_servico(linhas: list[dict]) -> None:
    """Qual serviço puxa o faturamento — nem sempre é o mais vendido."""
    concluidos = [r for r in linhas if r["status"] == "concluido"]
    if not concluidos:
        return

    st.subheader("Por serviço")
    contagem: dict[str, dict[str, int]] = {}
    for r in concluidos:
        alvo = contagem.setdefault(r["servicos"], {"qtd": 0, "total": 0})
        alvo["qtd"] += 1
        alvo["total"] += int(r["total_centavos"])

    st.dataframe(
        pd.DataFrame([
            {"Serviço": nome, "Concluídos": v["qtd"],
             "Faturamento": formato.reais(v["total"])}
            for nome, v in sorted(contagem.items(), key=lambda kv: -kv[1]["total"])
        ]), width="stretch", hide_index=True)
