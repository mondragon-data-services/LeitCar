"""Calculo de horarios livres (secao 6 da ARQUITETURA).

NAO importa streamlit. Recebe os fatos ja lidos do banco e faz a
subtracao: horario de funcionamento menos ocupacoes menos bloqueios.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
PASSO_MIN = 15
ANTECEDENCIA_MIN = 60


@dataclass(frozen=True)
class ConfigDia:
    dia_semana: int
    abre: time
    fecha: time
    qtd_boxes: int
    aberto: bool = True


@dataclass(frozen=True)
class Intervalo:
    """Espelha um tstzrange: lower inclusivo, upper exclusivo."""
    lower: datetime
    upper: datetime

    def colide(self, inicio: datetime, fim: datetime) -> bool:
        return self.lower < fim and self.upper > inicio


@dataclass(frozen=True)
class Ocupacao(Intervalo):
    box: int = 1


def dia_semana_bd(d: date) -> int:
    """Converte para a convencao do schema: 0 = domingo."""
    return (d.weekday() + 1) % 7


def duracao_total(servicos: dict[int, dict], carrinho: dict[int, int]) -> int:
    return sum(servicos[sid]["duracao_min"] * qtd
               for sid, qtd in carrinho.items() if sid in servicos)


def total_centavos(servicos: dict[int, dict], carrinho: dict[int, int]) -> int:
    return sum(servicos[sid]["preco_centavos"] * qtd
               for sid, qtd in carrinho.items() if sid in servicos)


def escolher_box(inicio: datetime, fim: datetime, ocupados, bloqueios,
                 qtd_boxes: int) -> int | None:
    """Primeiro box livre no intervalo, ou None se nao houver.

    A tela usa isso para ser gentil; a constraint EXCLUDE do banco
    e quem garante que dois cliques simultaneos nao passem juntos.
    """
    if any(b.colide(inicio, fim) for b in bloqueios):
        return None
    tomados = {o.box for o in ocupados if o.colide(inicio, fim)}
    for box in range(1, qtd_boxes + 1):
        if box not in tomados:
            return box
    return None


def horarios_livres(
    data: date,
    duracao_min: int,
    cfg: ConfigDia | None,
    ocupados,
    bloqueios,
    agora: datetime | None = None,
    antecedencia_min: int = ANTECEDENCIA_MIN,
    passo_min: int = PASSO_MIN,
) -> list[datetime]:
    """Slots que cabem inteiros dentro do expediente e tem box livre."""
    if duracao_min <= 0 or cfg is None or not cfg.aberto:
        return []

    agora = agora or datetime.now(TZ)
    abre = datetime.combine(data, cfg.abre, tzinfo=TZ)
    fecha = datetime.combine(data, cfg.fecha, tzinfo=TZ)
    duracao = timedelta(minutes=duracao_min)
    limite = agora + timedelta(minutes=antecedencia_min)

    livres: list[datetime] = []
    atual = abre
    while atual + duracao <= fecha:
        fim = atual + duracao
        if atual >= limite and escolher_box(atual, fim, ocupados, bloqueios,
                                            cfg.qtd_boxes) is not None:
            livres.append(atual)
        atual += timedelta(minutes=passo_min)
    return livres


def ocupacoes_vigentes(linhas, agora: datetime | None = None) -> list[Ocupacao]:
    """Expiracao preguicosa: pendente vencido deixa de ocupar o slot.

    `linhas` sao dicts com lower, upper, box, status e expira_em.
    """
    agora = agora or datetime.now(TZ)
    vivos = []
    for r in linhas:
        if r["status"] in ("cancelado", "expirado"):
            continue
        if r["status"] == "pendente" and r.get("expira_em") and r["expira_em"] < agora:
            continue
        vivos.append(Ocupacao(lower=r["lower"], upper=r["upper"], box=int(r["box"])))
    return vivos
