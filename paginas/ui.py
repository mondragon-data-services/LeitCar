"""Cara de site, nao de dashboard (secao 9 da ARQUITETURA)."""
from __future__ import annotations

import streamlit as st

from servicos import formato, loja, portfolio

CSS = """
<style>
  :root {
    --tinta:#0b1220; --grafite:#1c2536; --azul:#1d4ed8; --azul-claro:#3b82f6;
    --cinza:#5b6478; --linha:#e6e8ef; --areia:#f6f7fa;
  }
  #MainMenu, footer, header [data-testid="stToolbar"] {visibility: hidden;}
  header {height: 0rem;}
  .block-container {padding-top: 1rem; padding-bottom: 5rem; max-width: 48rem;}

  /* ---------------------------------------------------------- cabecalho */
  .lc-topo {position:relative; overflow:hidden; border-radius:18px;
            padding:1.6rem 1.3rem; margin-bottom:1.2rem; color:#fff;
            background:
              radial-gradient(120% 140% at 85% 0%, rgba(59,130,246,.45) 0%, transparent 55%),
              linear-gradient(135deg, #0b1220 0%, #1c2536 55%, #142046 100%);
            box-shadow:0 12px 30px -18px rgba(11,18,32,.85);}
  .lc-topo h1 {font-size:1.5rem; margin:0; line-height:1.15; color:#fff;
               letter-spacing:-.02em; font-weight:800;}
  .lc-topo .lc-tag {display:inline-block; font-size:.68rem; letter-spacing:.18em;
                    text-transform:uppercase; color:#93c5fd; font-weight:700;
                    margin-bottom:.45rem;}
  .lc-topo p {margin:.5rem 0 0; font-size:.9rem; color:#c7d2e5; max-width:32ch;}
  .lc-topo .lc-contato {margin-top:1rem; display:flex; flex-wrap:wrap; gap:.45rem;}
  .lc-topo .lc-contato a, .lc-topo .lc-contato span {
      background:rgba(255,255,255,.1); border:1px solid rgba(255,255,255,.16);
      color:#fff; text-decoration:none; font-size:.78rem; font-weight:600;
      padding:.32rem .7rem; border-radius:999px; backdrop-filter:blur(4px);}

  /* ------------------------------------------------------------- cards */
  .lc-secao {font-size:.7rem; letter-spacing:.16em; text-transform:uppercase;
             color:var(--cinza); font-weight:700; margin:1.6rem 0 .1rem;}
  .lc-secao-t {font-size:1.25rem; font-weight:800; letter-spacing:-.02em;
               color:var(--tinta); margin:.1rem 0 .9rem;}
  .lc-nome {font-size:1.08rem; font-weight:750; color:var(--tinta);
            letter-spacing:-.01em; margin:0;}
  .lc-sub {color:var(--cinza); font-size:.85rem; margin:.2rem 0 .1rem;}
  .lc-preco {font-weight:800; font-size:1.45rem; color:var(--tinta);
             letter-spacing:-.03em; line-height:1.1;}
  .lc-preco small {font-size:.72rem; font-weight:600; color:var(--cinza);
                   letter-spacing:0;}
  .lc-meta {color:var(--cinza); font-size:.8rem;}
  .lc-inclui {margin:.55rem 0 0; padding:0; list-style:none;}
  .lc-inclui li {font-size:.83rem; color:#3d4658; padding:.13rem 0 .13rem 1.15rem;
                 position:relative;}
  .lc-inclui li::before {content:"✓"; position:absolute; left:0; top:.1rem;
                         color:var(--azul); font-weight:800; font-size:.8rem;}
  .lc-escolhido {display:inline-block; background:#dbeafe; color:#1e40af;
                 font-size:.68rem; font-weight:800; letter-spacing:.1em;
                 text-transform:uppercase; padding:.2rem .55rem; border-radius:999px;}

  /* ---------------------------------------------------------- galeria */
  .lc-galeria {display:grid; gap:.55rem; margin:.2rem 0 .4rem;
               grid-template-columns:repeat(auto-fill, minmax(150px, 1fr));}
  .lc-foto {position:relative; aspect-ratio:4/3; border-radius:12px;
            overflow:hidden; background:var(--areia); border:1px solid var(--linha);}
  .lc-foto img {width:100%; height:100%; object-fit:cover; display:block;
                transition:transform .45s ease;}
  .lc-foto:hover img {transform:scale(1.06);}
  .lc-foto figcaption {position:absolute; left:0; right:0; bottom:0;
        font-size:.72rem; color:#fff; padding:1.4rem .6rem .45rem;
        background:linear-gradient(to top, rgba(6,10,20,.82), transparent);
        line-height:1.25;}
  .lc-foto::after {content:"⤢"; position:absolute; top:.4rem; right:.5rem;
        color:#fff; font-size:.8rem; line-height:1; padding:.22rem .35rem;
        border-radius:6px; background:rgba(6,10,20,.55); opacity:0;
        transition:opacity .2s ease;}
  .lc-foto:hover::after, .lc-foto:focus::after {opacity:1;}

  /* Lightbox em CSS puro: so aparece quando a URL aponta para o id dele. */
  .lc-lightbox {display:none;}
  .lc-lightbox:target {display:flex; position:fixed; inset:0; z-index:1000;
        align-items:center; justify-content:center; padding:1.2rem;
        background:rgba(6,10,20,.9); backdrop-filter:blur(3px);}
  .lc-lb-fundo {position:absolute; inset:0; cursor:zoom-out;}
  .lc-lb-caixa {position:relative; max-width:min(94vw, 60rem); max-height:92vh;
        display:flex; flex-direction:column; align-items:center; gap:.5rem;}
  .lc-lb-caixa img {max-width:100%; max-height:84vh; width:auto; height:auto;
        border-radius:12px; box-shadow:0 24px 60px -20px rgba(0,0,0,.9);
        object-fit:contain;}
  .lc-lb-legenda {margin:0; color:#e2e8f0; font-size:.85rem; text-align:center;}
  .lc-lb-x {position:absolute; top:.7rem; right:1rem; color:#fff; font-size:1.4rem;
        line-height:1; text-decoration:none; padding:.35rem .6rem; border-radius:10px;
        background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.2);}
  .lc-lb-x:hover {background:rgba(255,255,255,.22);}

  .lc-vazio {border:1px dashed var(--linha); border-radius:14px; padding:1.6rem 1rem;
             text-align:center; color:var(--cinza); font-size:.85rem;
             background:var(--areia);}

  /* ------------------------------------------------------------ resto */
  .lc-barra {position:sticky; bottom:0; background:#fff; border-top:1px solid var(--linha);
             padding:.7rem 0 .2rem; margin-top:1.2rem; z-index:5;}
  .lc-chip {display:inline-block; padding:.2rem .6rem; border-radius:999px;
            font-size:.75rem; font-weight:700;}
  .lc-pendente  {background:#fef3c7; color:#92400e;}
  .lc-confirmado{background:#dcfce7; color:#166534;}
  .lc-concluido {background:#dbeafe; color:#1e40af;}
  .lc-cancelado, .lc-expirado {background:#fee2e2; color:#991b1b;}
  .lc-rodape {margin-top:2.2rem; padding-top:1rem; border-top:1px solid var(--linha);
              color:var(--cinza); font-size:.78rem; line-height:1.6;}
  div[data-testid="stVerticalBlockBorderWrapper"] {background:#fff; border-radius:14px;}
  .stButton button {border-radius:10px; font-weight:650;}
</style>
"""


def aplicar_estilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def cabecalho(subtitulo: str = "Lavagem, detalhamento e higienização "
                              "com acabamento de loja especializada.") -> None:
    info = loja.info()
    tel = formato.telefone_humano(info["telefone"])
    wa = formato.telefone_wa(info["telefone"])
    st.markdown(
        f"""<div class="lc-topo">
              <span class="lc-tag">{info.get('cidade', '')}</span>
              <h1>{info['nome']}</h1>
              <p>{subtitulo}</p>
              <div class="lc-contato">
                <a href="https://wa.me/{wa}" target="_blank">WhatsApp {tel}</a>
                <span>{info['endereco']}</span>
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def secao(rotulo: str, titulo: str) -> None:
    st.markdown(f"<div class='lc-secao'>{rotulo}</div>"
                f"<div class='lc-secao-t'>{titulo}</div>", unsafe_allow_html=True)


def rodape() -> None:
    info = loja.info()
    st.markdown(
        f"""<div class="lc-rodape">
              <b>{info['nome']}</b><br>{info['endereco']}<br>
              WhatsApp {formato.telefone_humano(info['telefone'])}
            </div>""",
        unsafe_allow_html=True)


def galeria_html(fotos: list[dict]) -> str:
    """Grade clicavel: a miniatura abre a foto grande sobre a pagina.

    O lightbox e CSS puro, via `:target`. Clicar na miniatura poe
    `#foto-12` no hash da URL e o overlay correspondente aparece; o X
    volta para `#_` e ele some. Sem JavaScript, que o Streamlit remove
    do markdown, e sem mexer nos query params do roteamento.
    """
    celulas, overlays = [], []
    for f in fotos:
        fid = int(f["id"])
        legenda = (f.get("legenda") or "").strip()
        alt = legenda or "Trabalho realizado"
        rodape_foto = f"<figcaption>{legenda}</figcaption>" if legenda else ""
        celulas.append(
            f'<a class="lc-foto" href="#foto-{fid}" title="Ver em tamanho grande">'
            f'<img loading="lazy" alt="{alt}" src="{portfolio.url(f["arquivo"], thumb=True)}">'
            f'{rodape_foto}</a>')
        legenda_grande = f'<p class="lc-lb-legenda">{legenda}</p>' if legenda else ""
        overlays.append(
            f'<div class="lc-lightbox" id="foto-{fid}">'
            f'<a class="lc-lb-fundo" href="#_" aria-label="Fechar"></a>'
            f'<div class="lc-lb-caixa">'
            f'<img alt="{alt}" src="{portfolio.url(f["arquivo"])}">'
            f'{legenda_grande}</div>'
            f'<a class="lc-lb-x" href="#_" aria-label="Fechar">✕</a>'
            f'</div>')
    if not celulas:
        return ""
    return f"<div class='lc-galeria'>{''.join(celulas)}</div>{''.join(overlays)}"


ROTULOS_STATUS = {"pendente": "Aguardando pagamento", "confirmado": "Confirmado",
                  "concluido": "Concluído", "cancelado": "Cancelado",
                  "expirado": "Expirado"}


def chip_status(status: str) -> str:
    return (f'<span class="lc-chip lc-{status}">'
            f'{ROTULOS_STATUS.get(status, status)}</span>')


def rerun_bloco() -> None:
    """Reroda so o fragmento quando da; senao, reroda a pagina.

    `scope="fragment"` so e aceito durante um rerun de fragmento. Na
    primeira execucao da pagina (rerun de app inteiro) o Streamlit
    recusa, e ai o certo e rerodar tudo. RerunException herda de
    BaseException, entao o `except Exception` abaixo pega so o erro de
    escopo e nunca engole o sinal de rerun.
    """
    try:
        st.rerun(scope="fragment")
    except Exception:
        st.rerun()


def ir_para(**params) -> None:
    """Navega mexendo so nos query params, preservando o carrinho."""
    for chave, valor in params.items():
        if valor is None:
            st.query_params.pop(chave, None)
        else:
            st.query_params[chave] = str(valor)
    st.rerun()
