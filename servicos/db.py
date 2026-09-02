"""Acesso a dados via st.connection (secao 3 da ARQUITETURA).

Este e o unico modulo de `servicos/` que fala com o banco. A regra de
negocio vive em agenda.py e nao sabe que Postgres existe.
"""
from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta

import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from servicos import formato, portfolio
from servicos.agenda import TZ, ConfigDia, Intervalo, Ocupacao, dia_semana_bd

MINUTOS_PARA_PAGAR = 30


class SlotIndisponivel(Exception):
    """Todos os boxes do horario foram tomados entre a tela e o commit."""


RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def conexao():
    url = os.getenv("DATABASE_URL")
    if url:
        return st.connection("postgresql", type="sql", url=url)
    return st.connection("postgresql", type="sql")


def _sql(nome: str) -> str:
    with open(os.path.join(RAIZ, "sql", nome), encoding="utf-8") as f:
        return f.read()


def _tabelas_esperadas() -> set[str]:
    """Le os nomes direto do schema.sql, para nao virar lista desatualizada."""
    import re
    return set(re.findall(r"create table if not exists (\w+)", _sql("001_schema.sql")))


@st.cache_resource
def garantir_schema() -> str:
    """Aplica schema e seed uma vez por processo, e so quando falta algo.

    Em hospedagem sem shell (Streamlit Cloud) nao da para rodar psql na
    mao. Os dois arquivos sao idempotentes — tudo `if not exists` e
    `on conflict do nothing` — mas rodar o DDL inteiro custa alguns
    segundos contra um banco remoto, e isso apareceria na cara do
    primeiro visitante depois de cada deploy. Entao a gente confere
    antes e so paga o preco quando ha o que criar.
    """
    conn = conexao()
    with conn.session as s:
        existentes = {r[0] for r in s.execute(text(
            "select table_name from information_schema.tables "
            "where table_schema = 'public'")).all()}
    if _tabelas_esperadas() <= existentes:
        return "ja estava criado"

    for nome in ("001_schema.sql", "002_seed.sql"):
        with conn.session as s:
            s.execute(text(_sql(nome)))
            s.commit()
    return "criado agora"


# --------------------------------------------------------------------- leitura

def listar_servicos(incluir_inativos: bool = False) -> list[dict]:
    filtro = "" if incluir_inativos else "where ativo"
    df = conexao().query(f"select * from servicos {filtro} order by ordem, id", ttl=300)
    return df.to_dict("records")


def mapa_servicos(incluir_inativos: bool = True) -> dict[int, dict]:
    return {int(s["id"]): s for s in listar_servicos(incluir_inativos)}


def itens_por_servico() -> dict[int, list[str]]:
    """O que esta incluso em cada servico, na ordem de exibicao."""
    df = conexao().query(
        "select servico_id, descricao from servico_itens order by servico_id, ordem, id",
        ttl=300)
    saida: dict[int, list[str]] = {}
    for _, r in df.iterrows():
        saida.setdefault(int(r["servico_id"]), []).append(r["descricao"])
    return saida


def salvar_itens_servico(servico_id: int, descricoes: list[str]) -> None:
    conn = conexao()
    with conn.session as s:
        s.execute(text("delete from servico_itens where servico_id = :sid"),
                  {"sid": int(servico_id)})
        for ordem, d in enumerate((x.strip() for x in descricoes), start=1):
            if d:
                s.execute(text("""
                    insert into servico_itens (servico_id, ordem, descricao)
                    values (:sid, :ordem, :d)
                """), {"sid": int(servico_id), "ordem": ordem, "d": d})
        s.commit()
    st.cache_data.clear()


# ------------------------------------------------------------------------ porte

def listar_portes(incluir_inativos: bool = False) -> list[dict]:
    filtro = "" if incluir_inativos else "where ativo"
    df = conexao().query(f"select * from portes {filtro} order by ordem, codigo", ttl=300)
    return df.to_dict("records")


def buscar_porte(codigo: str) -> dict | None:
    for p in listar_portes(incluir_inativos=True):
        if p["codigo"] == codigo:
            return p
    return None


def acrescimo_do_porte(codigo: str | None) -> int:
    porte = buscar_porte(codigo) if codigo else None
    return int(porte["acrescimo_centavos"]) if porte else 0


def salvar_portes(linhas: list[dict]) -> None:
    conn = conexao()
    with conn.session as s:
        for r in linhas:
            codigo = (r.get("codigo") or "").strip().lower()
            if not codigo:
                continue
            s.execute(text("""
                insert into portes (codigo, nome, acrescimo_centavos, ordem, ativo)
                values (:codigo, :nome, :acrescimo, :ordem, :ativo)
                on conflict (codigo) do update set
                  nome = excluded.nome,
                  acrescimo_centavos = excluded.acrescimo_centavos,
                  ordem = excluded.ordem, ativo = excluded.ativo
            """), {"codigo": codigo, "nome": r.get("nome") or codigo.title(),
                   "acrescimo": int(r.get("acrescimo_centavos") or 0),
                   "ordem": int(r.get("ordem") or 0),
                   "ativo": bool(r.get("ativo", True))})
        s.commit()
    st.cache_data.clear()


def listar_horarios() -> list[dict]:
    df = conexao().query("select * from horario_funcionamento order by dia_semana",
                         ttl=300)
    return df.to_dict("records")


def _para_time(valor) -> time:
    return valor if isinstance(valor, time) else time.fromisoformat(str(valor))


def buscar_config(d: date) -> ConfigDia | None:
    for h in listar_horarios():
        if int(h["dia_semana"]) == dia_semana_bd(d):
            return ConfigDia(
                dia_semana=int(h["dia_semana"]),
                abre=_para_time(h["abre"]),
                fecha=_para_time(h["fecha"]),
                qtd_boxes=int(h["qtd_boxes"]),
                aberto=bool(h["aberto"]),
            )
    return None


def _janela(d: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(d, time(0, 0), tzinfo=TZ)
    return inicio, inicio + timedelta(days=1)


def buscar_ocupados(d: date) -> list[Ocupacao]:
    """Ignora cancelado, expirado e pendente vencido.

    Expiracao preguicosa: o carrinho abandonado libera o slot sozinho,
    sem cron e sem worker.
    """
    ini, fim = _janela(d)
    df = conexao().query(
        """
        select box, lower(periodo) as inicio, upper(periodo) as fim
        from agendamentos
        where periodo && tstzrange(:ini, :fim, '[)')
          and status not in ('cancelado', 'expirado')
          and not (status = 'pendente' and expira_em is not null and expira_em < now())
        """,
        params={"ini": ini, "fim": fim}, ttl=0,
    )
    return [Ocupacao(lower=r["inicio"].astimezone(TZ),
                     upper=r["fim"].astimezone(TZ),
                     box=int(r["box"])) for _, r in df.iterrows()]


def buscar_bloqueios(d: date) -> list[Intervalo]:
    ini, fim = _janela(d)
    df = conexao().query(
        """
        select lower(periodo) as inicio, upper(periodo) as fim
        from bloqueios
        where periodo && tstzrange(:ini, :fim, '[)')
        """,
        params={"ini": ini, "fim": fim}, ttl=0,
    )
    return [Intervalo(lower=r["inicio"].astimezone(TZ),
                      upper=r["fim"].astimezone(TZ)) for _, r in df.iterrows()]


def buscar_agendamento(codigo: str) -> dict | None:
    df = conexao().query(
        """
        select a.*, lower(a.periodo) as inicio, upper(a.periodo) as fim
        from agendamentos a where a.codigo = :codigo
        """,
        params={"codigo": (codigo or "").strip().upper()}, ttl=0,
    )
    if df.empty:
        return None
    pedido = df.to_dict("records")[0]
    pedido["itens"] = conexao().query(
        "select * from agendamento_itens where agendamento_id = :aid order by id",
        params={"aid": int(pedido["id"])}, ttl=0,
    ).to_dict("records")
    return pedido


def agendamentos_do_dia(d: date) -> list[dict]:
    ini, fim = _janela(d)
    df = conexao().query(
        """
        select id, codigo, cliente_nome, cliente_telefone, veiculo_placa,
               veiculo_modelo, porte_codigo, box, total_centavos, status, expira_em,
               lower(periodo) as inicio, upper(periodo) as fim
        from agendamentos
        where periodo && tstzrange(:ini, :fim, '[)')
        order by lower(periodo), box
        """,
        params={"ini": ini, "fim": fim}, ttl=0,
    )
    return df.to_dict("records")


# -------------------------------------------------------------------- portfolio

def listar_portfolio(incluir_inativos: bool = False, limite: int | None = None) -> list[dict]:
    filtro = "" if incluir_inativos else "where p.ativo"
    limite_sql = f"limit {int(limite)}" if limite else ""
    df = conexao().query(
        f"""
        select p.id, p.arquivo, p.legenda, p.servico_id, p.ordem, p.ativo,
               s.nome as servico_nome
        from portfolio p
        left join servicos s on s.id = p.servico_id
        {filtro}
        order by p.ordem, p.id desc
        {limite_sql}
        """, ttl=60)
    return df.to_dict("records")


def adicionar_foto(arquivo: str, legenda: str = "", servico_id: int | None = None) -> bool:
    """Insere a foto na galeria. False quando ela ja estava la.

    Guarda tambem os bytes: em hospedagem com disco efemero a pasta
    `static/` some a cada deploy, e sem isso a galeria voltaria vazia.

    O nome do arquivo carrega o hash do conteudo, entao o `do nothing`
    aqui e o que impede a mesma foto de aparecer duas vezes.
    """
    conn = conexao()
    with conn.session as s:
        proxima = s.execute(text(
            "select coalesce(max(ordem), 0) + 1 from portfolio")).scalar_one()
        novo = s.execute(text("""
            insert into portfolio (arquivo, legenda, servico_id, ordem,
                                   imagem, miniatura)
            values (:arquivo, :legenda, :sid, :ordem, :imagem, :miniatura)
            on conflict (arquivo) do nothing
            returning id
        """), {"arquivo": arquivo, "legenda": legenda, "sid": servico_id,
               "ordem": int(proxima),
               "imagem": portfolio.bytes_de(arquivo),
               "miniatura": portfolio.bytes_de(arquivo, thumb=True)}).scalar()
        s.commit()
    st.cache_data.clear()
    return novo is not None


def materializar_fotos(apenas: list[str] | None = None) -> int:
    """Repoe no disco as fotos que so existem no banco.

    O Streamlit serve as imagens de `static/`, mas esse diretorio nao
    sobrevive a um redeploy. Aqui o banco reescreve o que faltar, e o
    disco passa a ser so um cache.

    `apenas` limita aos arquivos que a tela vai mostrar. Sem isso, o
    primeiro visitante depois de um deploy espera o download da galeria
    inteira; com isso, espera so o que vai ver.
    """
    candidatos = (apenas if apenas is not None
                  else [f["arquivo"] for f in listar_portfolio(incluir_inativos=True)])
    faltando = [{"arquivo": a} for a in candidatos
                if not portfolio.existe(a)
                or not portfolio.caminho_thumb(a).is_file()]
    if not faltando:
        return 0

    # Sem conn.query() aqui: ele guarda o resultado com pickle, e o bytea
    # volta do psycopg2 como memoryview, que nao e serializavel.
    conn = conexao()
    repostas = 0
    with conn.session as s:
        linhas = s.execute(text(
            "select arquivo, imagem, miniatura from portfolio "
            "where arquivo = any(:nomes)"),
            {"nomes": [f["arquivo"] for f in faltando]}).all()
    for arquivo, imagem, miniatura in linhas:
        if portfolio.gravar_bytes(arquivo,
                                  bytes(imagem) if imagem else None,
                                  bytes(miniatura) if miniatura else None):
            repostas += 1
    return repostas


def preencher_bytes_faltantes() -> int:
    """Sobe para o banco os bytes das fotos que so existem no disco.

    Serve para as fotos importadas antes de o banco passar a guardar a
    imagem. Roda uma vez e nao faz nada nas vezes seguintes.
    """
    conn = conexao()
    enviadas = 0
    with conn.session as s:
        pendentes = [r[0] for r in s.execute(text(
            "select arquivo from portfolio where imagem is null")).all()]
        for arquivo in pendentes:
            imagem = portfolio.bytes_de(arquivo)
            if not imagem:
                continue
            s.execute(text("""
                update portfolio set imagem = :img, miniatura = :thumb
                where arquivo = :arquivo
            """), {"img": imagem,
                   "thumb": portfolio.bytes_de(arquivo, thumb=True),
                   "arquivo": arquivo})
            enviadas += 1
        s.commit()
    return enviadas


def salvar_portfolio(linhas: list[dict]) -> None:
    conn = conexao()
    with conn.session as s:
        for r in linhas:
            s.execute(text("""
                update portfolio set legenda = :legenda, servico_id = :sid,
                                     ordem = :ordem, ativo = :ativo
                where id = :id
            """), {"id": int(r["id"]), "legenda": r.get("legenda") or "",
                   "sid": int(r["servico_id"]) if r.get("servico_id") else None,
                   "ordem": int(r.get("ordem") or 0),
                   "ativo": bool(r.get("ativo", True))})
        s.commit()
    st.cache_data.clear()


def remover_foto(foto_id: int) -> str | None:
    """Apaga a linha e devolve o arquivo, para o chamador remover do disco."""
    conn = conexao()
    with conn.session as s:
        arquivo = s.execute(text(
            "delete from portfolio where id = :id returning arquivo"),
            {"id": int(foto_id)}).scalar()
        s.commit()
    st.cache_data.clear()
    return arquivo


# ---------------------------------------------------------------------- escrita

def expirar_pendentes() -> None:
    conn = conexao()
    with conn.session as s:
        s.execute(text("""
            update agendamentos set status = 'expirado'
            where status = 'pendente' and expira_em is not null and expira_em < now()
        """))
        s.commit()


def criar_agendamento(*, nome: str, telefone: str, placa: str, modelo: str,
                      inicio: datetime, duracao_min: int, itens: list[dict],
                      qtd_boxes: int, exige_pagamento: bool,
                      porte_codigo: str | None = None) -> str:
    """Insercao transacional escolhendo o primeiro box livre.

    A tela ja filtrou os slots, mas o rerun do Streamlit torna facil
    executar isso duas vezes. Quem garante a correcao e a constraint
    EXCLUDE: se o box foi tomado, o insert levanta IntegrityError e a
    gente tenta o proximo.
    """
    expirar_pendentes()

    fim = inicio + timedelta(minutes=duracao_min)
    total = sum(int(i["preco_centavos"]) for i in itens)
    status = "pendente" if exige_pagamento else "confirmado"
    expira = (datetime.now(TZ) + timedelta(minutes=MINUTOS_PARA_PAGAR)
              if exige_pagamento else None)

    conn = conexao()
    for box in range(1, qtd_boxes + 1):
        for _ in range(5):                     # colisao de codigo e rara
            codigo = formato.gerar_codigo()
            try:
                with conn.session as s:
                    aid = s.execute(text("""
                        insert into agendamentos
                          (codigo, cliente_nome, cliente_telefone, veiculo_placa,
                           veiculo_modelo, porte_codigo, box, periodo,
                           total_centavos, status, expira_em)
                        values
                          (:codigo, :nome, :telefone, :placa, :modelo, :porte, :box,
                           tstzrange(:ini, :fim, '[)'), :total, :status, :expira)
                        returning id
                    """), {"codigo": codigo, "nome": nome, "telefone": telefone,
                           "placa": placa, "modelo": modelo, "box": box,
                           "porte": porte_codigo, "ini": inicio, "fim": fim,
                           "total": total, "status": status,
                           "expira": expira}).scalar_one()
                    for it in itens:
                        s.execute(text("""
                            insert into agendamento_itens
                              (agendamento_id, servico_id, nome_snapshot,
                               preco_centavos, duracao_min)
                            values (:aid, :sid, :nome, :preco, :dur)
                        """), {"aid": aid,
                               # servico_id nulo = linha de acrescimo de porte
                               "sid": (int(it["servico_id"])
                                       if it.get("servico_id") else None),
                               "nome": it["nome"], "preco": int(it["preco_centavos"]),
                               "dur": int(it["duracao_min"])})
                    s.commit()
                return codigo
            except IntegrityError as e:
                detalhe = str(getattr(e, "orig", e))
                if "sem_overbooking" in detalhe:
                    break                      # box tomado, tenta o proximo box
                if "codigo" in detalhe:
                    continue                   # sorteia outro codigo
                raise
    raise SlotIndisponivel()


def mudar_status(codigo: str, status: str) -> None:
    conn = conexao()
    with conn.session as s:
        s.execute(text("update agendamentos set status = :st where codigo = :codigo"),
                  {"st": status, "codigo": codigo})
        s.commit()


def salvar_servicos(linhas: list[dict]) -> None:
    conn = conexao()
    with conn.session as s:
        for r in linhas:
            dados = {"nome": (r.get("nome") or "").strip(),
                     "descricao": r.get("descricao") or "",
                     "preco": int(r.get("preco_centavos") or 0),
                     "dur": int(r.get("duracao_min") or 0),
                     "ativo": bool(r.get("ativo")),
                     "ordem": int(r.get("ordem") or 0)}
            if not dados["nome"] or dados["dur"] <= 0:
                continue
            rid = r.get("id")
            if rid is None or (isinstance(rid, float) and rid != rid):
                s.execute(text("""
                    insert into servicos (nome, descricao, preco_centavos, duracao_min, ativo, ordem)
                    values (:nome, :descricao, :preco, :dur, :ativo, :ordem)
                """), dados)
            else:
                s.execute(text("""
                    update servicos set nome=:nome, descricao=:descricao,
                      preco_centavos=:preco, duracao_min=:dur, ativo=:ativo, ordem=:ordem
                    where id=:id
                """), {**dados, "id": int(rid)})
        s.commit()
    st.cache_data.clear()


def desativar_servicos(ids: list[int]) -> None:
    if not ids:
        return
    conn = conexao()
    with conn.session as s:
        s.execute(text("update servicos set ativo = false where id = any(:ids)"),
                  {"ids": [int(i) for i in ids]})
        s.commit()
    st.cache_data.clear()


def salvar_horarios(linhas: list[dict]) -> None:
    conn = conexao()
    with conn.session as s:
        for r in linhas:
            s.execute(text("""
                insert into horario_funcionamento (dia_semana, abre, fecha, qtd_boxes, aberto)
                values (:dia, :abre, :fecha, :boxes, :aberto)
                on conflict (dia_semana) do update set
                  abre = excluded.abre, fecha = excluded.fecha,
                  qtd_boxes = excluded.qtd_boxes, aberto = excluded.aberto
            """), {"dia": int(r["dia_semana"]), "abre": _para_time(r["abre"]),
                   "fecha": _para_time(r["fecha"]), "boxes": int(r["qtd_boxes"]),
                   "aberto": bool(r["aberto"])})
        s.commit()
    st.cache_data.clear()


def listar_bloqueios(desde: date | None = None) -> list[dict]:
    corte = datetime.combine(desde, time(0, 0), tzinfo=TZ) if desde else datetime.now(TZ)
    df = conexao().query(
        """
        select id, motivo, lower(periodo) as inicio, upper(periodo) as fim
        from bloqueios
        where upper(periodo) >= :corte
        order by lower(periodo)
        """,
        params={"corte": corte}, ttl=0,
    )
    return df.to_dict("records")


def criar_bloqueio(inicio: datetime, fim: datetime, motivo: str) -> None:
    conn = conexao()
    with conn.session as s:
        s.execute(text("""
            insert into bloqueios (periodo, motivo)
            values (tstzrange(:ini, :fim, '[)'), :motivo)
        """), {"ini": inicio, "fim": fim, "motivo": motivo})
        s.commit()


def remover_bloqueio(bloqueio_id: int) -> None:
    conn = conexao()
    with conn.session as s:
        s.execute(text("delete from bloqueios where id = :id"), {"id": int(bloqueio_id)})
        s.commit()
