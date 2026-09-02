"""Gera a landing estatica do SEO a partir do banco (secao 2.5).

Roda fora do Streamlit — de proposito. Um cron diario chama
`python landing/gerar_landing.py` e a landing acompanha o catalogo:
preco mudou no admin, a pagina publica atualiza sozinha. As fotos do
portfolio sao copiadas junto, para o Nginx servir.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from servicos import portfolio  # noqa: E402
from servicos.formato import duracao_humana, reais, telefone_humano, telefone_wa  # noqa: E402

NOMES_DIA = {0: "Domingo", 1: "Segunda", 2: "Terça", 3: "Quarta",
             4: "Quinta", 5: "Sexta", 6: "Sábado"}
DIAS_SCHEMA = {0: "Sunday", 1: "Monday", 2: "Tuesday", 3: "Wednesday",
               4: "Thursday", 5: "Friday", 6: "Saturday"}
MAX_FOTOS = 12


def ler_secrets() -> dict:
    caminho = RAIZ / ".streamlit" / "secrets.toml"
    if not caminho.exists():
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        return {}
    return tomllib.loads(caminho.read_text(encoding="utf-8"))


def url_banco(secrets: dict) -> str:
    if url := os.getenv("DATABASE_URL"):
        return url
    conn = secrets.get("connections", {}).get("postgresql", {})
    if conn.get("url"):
        return conn["url"]
    raise SystemExit("Defina DATABASE_URL ou [connections.postgresql] url em secrets.toml")


def carregar(url: str) -> dict:
    from sqlalchemy import create_engine, text

    eng = create_engine(url)
    with eng.connect() as c:
        def linhas(sql):
            return [dict(r) for r in c.execute(text(sql)).mappings()]

        dados = {
            "servicos": linhas("select id, nome, descricao, preco_centavos, duracao_min "
                               "from servicos where ativo order by ordem, id"),
            "itens": linhas("select servico_id, descricao from servico_itens "
                            "order by servico_id, ordem, id"),
            "portes": linhas("select codigo, nome, acrescimo_centavos from portes "
                             "where ativo order by ordem, codigo"),
            "horarios": linhas("select dia_semana, abre, fecha, aberto "
                               "from horario_funcionamento order by dia_semana"),
            "fotos": linhas("select arquivo, legenda from portfolio where ativo "
                            f"order by ordem, id desc limit {MAX_FOTOS}"),
        }
    return dados


def json_ld(info: dict, dados: dict) -> str:
    estrutura = {
        "@context": "https://schema.org",
        "@type": "AutoWash",
        "name": info["nome"],
        "address": {"@type": "PostalAddress", "streetAddress": info["endereco"],
                    "addressLocality": info["cidade"], "addressCountry": "BR"},
        "telephone": "+" + telefone_wa(info["telefone"]),
        "url": info["url_site"],
        "priceRange": "$$",
        "openingHoursSpecification": [
            {"@type": "OpeningHoursSpecification",
             "dayOfWeek": f"https://schema.org/{DIAS_SCHEMA[int(h['dia_semana'])]}",
             "opens": str(h["abre"])[:5], "closes": str(h["fecha"])[:5]}
            for h in dados["horarios"] if h["aberto"]
        ],
        "hasOfferCatalog": {
            "@type": "OfferCatalog", "name": "Serviços",
            "itemListElement": [
                {"@type": "Offer",
                 "itemOffered": {"@type": "Service", "name": s["nome"],
                                 "description": s["descricao"] or ""},
                 "price": f"{int(s['preco_centavos']) / 100:.2f}",
                 "priceCurrency": "BRL"}
                for s in dados["servicos"]
            ],
        },
    }
    return json.dumps(estrutura, ensure_ascii=False)


def copiar_fotos(fotos: list[dict], destino_dir: Path) -> list[dict]:
    """Copia miniatura e original para junto do HTML.

    A miniatura vai em `fotos/` e alimenta a grade; a versao grande vai
    em `fotos/grandes/` e e o que abre quando o visitante clica.
    """
    pasta = destino_dir / "fotos"
    pasta_grandes = pasta / "grandes"
    pasta_grandes.mkdir(parents=True, exist_ok=True)
    saida = []
    for f in fotos:
        grande = portfolio.caminho(f["arquivo"])
        if not grande.is_file():
            continue
        thumb = portfolio.caminho_thumb(f["arquivo"])
        shutil.copy2(thumb if thumb.is_file() else grande, pasta / f["arquivo"])
        shutil.copy2(grande, pasta_grandes / f["arquivo"])
        saida.append(f)
    return saida


def gerar(destino: Path) -> Path:
    secrets = ler_secrets()
    info = {"nome": "Leite Estética Automotiva", "telefone": "14998904665",
            "endereco": "Duartina - SP", "cidade": "Duartina",
            "url_publica": "http://localhost:8501",
            "chamada": "Lavagem, detalhamento e higienização com acabamento "
                       "de loja especializada."}
    info.update(secrets.get("loja", {}))
    info["url_site"] = os.getenv("URL_SITE", info.get("url_site", "http://localhost:8080"))

    dados = carregar(url_banco(secrets))
    itens: dict[int, list[str]] = {}
    for i in dados["itens"]:
        itens.setdefault(int(i["servico_id"]), []).append(i["descricao"])

    blocos = []
    for s in dados["servicos"]:
        lista = "".join(f"<li>{d}</li>" for d in itens.get(int(s["id"]), []))
        blocos.append(
            f'  <div class="servico">\n'
            f'    <div class="topo"><h3>{s["nome"]}</h3>'
            f'<div class="preco">{reais(int(s["preco_centavos"]))}'
            f'<small>{duracao_humana(int(s["duracao_min"]))}</small></div></div>\n'
            f'    <p class="nota">{s["descricao"] or ""}</p>\n'
            f'    <ul>{lista}</ul>\n'
            f'  </div>')

    portes = dados["portes"] or [{"nome": "Carro", "acrescimo_centavos": 0}]
    cabecalho_portes = "".join(f"<th>{p['nome']}</th>" for p in portes)
    linhas_matriz = "\n".join(
        f'      <tr><td>{s["nome"]}</td>' + "".join(
            f'<td class="num">'
            f'{reais(int(s["preco_centavos"]) + int(p["acrescimo_centavos"]))}</td>'
            for p in portes) + "</tr>"
        for s in dados["servicos"])

    fotos = copiar_fotos(dados["fotos"], destino.parent)
    if fotos:
        celulas = "".join(
            f'<figure><a href="fotos/grandes/{f["arquivo"]}" target="_blank" '
            f'title="Ver em tamanho grande">'
            f'<img loading="lazy" src="fotos/{f["arquivo"]}" '
            f'alt="{f["legenda"] or "Trabalho realizado"}">'
            + (f'<figcaption>{f["legenda"]}</figcaption>' if f["legenda"] else "")
            + "</a></figure>"
            for f in fotos)
        secao_galeria = ('  <div class="rotulo">Portfólio</div>\n'
                         '  <h2>Trabalhos que saíram daqui</h2>\n'
                         f'  <div class="galeria">{celulas}</div>')
    else:
        secao_galeria = ""

    linhas_horarios = "\n".join(
        f'      <tr><td>{NOMES_DIA[int(h["dia_semana"])]}</td>'
        f'<td class="num">'
        f'{"Fechado" if not h["aberto"] else str(h["abre"])[:5] + " às " + str(h["fecha"])[:5]}'
        f'</td></tr>'
        for h in dados["horarios"])

    html = (RAIZ / "landing" / "template.html").read_text(encoding="utf-8").format(
        nome=info["nome"],
        cidade=info["cidade"],
        chamada=info["chamada"],
        endereco=info["endereco"],
        telefone=telefone_humano(info["telefone"]),
        telefone_wa=telefone_wa(info["telefone"]),
        descricao_seo=(f'{info["nome"]}: lavagem, detalhamento e higienização '
                       f'em {info["cidade"]}. Agende online e escolha seu horário.'),
        url_site=info["url_site"],
        url_app=info["url_publica"],
        json_ld=json_ld(info, dados),
        blocos_servicos="\n".join(blocos),
        cabecalho_portes=cabecalho_portes,
        linhas_matriz=linhas_matriz,
        secao_galeria=secao_galeria,
        linhas_horarios=linhas_horarios,
        gerado_em=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )

    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
    return destino


if __name__ == "__main__":
    saida = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "landing" / "dist" / "index.html"
    print(f"landing gerada em {gerar(saida)}")
