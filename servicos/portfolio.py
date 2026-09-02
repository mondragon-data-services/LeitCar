"""Armazenamento das fotos do portfolio.

Os arquivos moram em `static/portfolio/`, que o Streamlit serve por HTTP
em `/app/static/`. O banco guarda so o nome e os metadados. Nao importa streamlit: da para importar uma pasta inteira por
linha de comando, sem subir o app.

Toda foto entra normalizada — orientacao do EXIF aplicada, redimensionada
e recomprimida — porque foto de celular tem 4 MB e 4000 px de largura, e
isso deixaria a vitrine lenta no 4G do cliente.
"""
from __future__ import annotations

import hashlib
import io
import re
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "static" / "portfolio"      # servido pelo Streamlit em /app/static/
PASTA_THUMBS = PASTA / "thumbs"
URL_BASE = "app/static/portfolio"
PASTA_ENTRADA = RAIZ / "fotos"          # pasta de deposito para importacao

EXTENSOES = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".bmp", ".tif", ".tiff"}
LARGURA_MAX = 1600
LARGURA_THUMB = 640
QUALIDADE = 85
TAMANHO_MAX_BYTES = 25 * 1024 * 1024


class ImagemInvalida(Exception):
    pass


def _pillow():
    from PIL import Image, ImageOps
    try:                                # HEIC/HEIF do iPhone
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    return Image, ImageOps


def _slug(texto: str) -> str:
    base = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base).strip("-").lower()
    return (base or "foto")[:40]


def _garantir_pastas() -> None:
    PASTA_THUMBS.mkdir(parents=True, exist_ok=True)


def caminho(arquivo: str) -> Path:
    return PASTA / arquivo


def caminho_thumb(arquivo: str) -> Path:
    return PASTA_THUMBS / arquivo


def existe(arquivo: str) -> bool:
    return caminho(arquivo).is_file()


def salvar(dados: bytes, nome_original: str) -> str:
    """Normaliza e grava a imagem. Devolve o nome do arquivo final.

    O nome carrega um hash do conteudo, entao subir a mesma foto duas
    vezes gera o mesmo arquivo em vez de duplicar a galeria.
    """
    if not dados:
        raise ImagemInvalida("Arquivo vazio.")
    if len(dados) > TAMANHO_MAX_BYTES:
        raise ImagemInvalida("Arquivo maior que 25 MB.")

    Image, ImageOps = _pillow()
    try:
        img = Image.open(io.BytesIO(dados))
        img.load()
    except Exception as e:
        raise ImagemInvalida(f"Nao consegui ler a imagem: {e}") from e

    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    digest = hashlib.sha256(dados).hexdigest()[:10]
    arquivo = f"{_slug(Path(nome_original).stem)}-{digest}.jpg"

    _garantir_pastas()
    grande = img.copy()
    grande.thumbnail((LARGURA_MAX, LARGURA_MAX), Image.LANCZOS)
    grande.convert("RGB").save(caminho(arquivo), "JPEG",
                               quality=QUALIDADE, optimize=True)

    thumb = img.copy()
    thumb.thumbnail((LARGURA_THUMB, LARGURA_THUMB), Image.LANCZOS)
    thumb.convert("RGB").save(caminho_thumb(arquivo), "JPEG",
                              quality=80, optimize=True)
    return arquivo


def remover(arquivo: str) -> None:
    for p in (caminho(arquivo), caminho_thumb(arquivo)):
        p.unlink(missing_ok=True)


def listar_pendentes(origem: Path | None = None) -> list[Path]:
    """Fotos largadas na pasta `fotos/` que ainda dao para importar."""
    origem = origem or PASTA_ENTRADA
    if not origem.is_dir():
        return []
    return sorted(p for p in origem.rglob("*")
                  if p.is_file() and p.suffix.lower() in EXTENSOES)


def importar_pasta(origem: Path | None = None) -> list[tuple[str, str]]:
    """Importa tudo que estiver na pasta. Devolve (arquivo, nome_original).

    Idempotente: o nome do arquivo vem do hash do conteudo, entao rodar
    duas vezes nao duplica nada.
    """
    resultados = []
    for caminho_origem in listar_pendentes(origem):
        try:
            arquivo = salvar(caminho_origem.read_bytes(), caminho_origem.name)
        except ImagemInvalida:
            continue
        resultados.append((arquivo, caminho_origem.name))
    return resultados


def bytes_de(arquivo: str, thumb: bool = False) -> bytes | None:
    p = caminho_thumb(arquivo) if thumb else caminho(arquivo)
    if not p.is_file():
        p = caminho(arquivo)
    return p.read_bytes() if p.is_file() else None


def url(arquivo: str, thumb: bool = False) -> str:
    """URL publica do arquivo, servida pelo static serving do Streamlit.

    Relativa de proposito: funciona igual em localhost, atras do Nginx e
    em subpasta, sem ninguem ter que configurar dominio.
    """
    return f"{URL_BASE}/thumbs/{arquivo}" if thumb else f"{URL_BASE}/{arquivo}"


def gravar_bytes(arquivo: str, imagem: bytes | None,
                 miniatura: bytes | None = None) -> bool:
    """Repoe no disco uma foto que veio do banco. Nao sobrescreve o que existe."""
    if not imagem:
        return False
    _garantir_pastas()
    if not caminho(arquivo).is_file():
        caminho(arquivo).write_bytes(imagem)
    if not caminho_thumb(arquivo).is_file():
        caminho_thumb(arquivo).write_bytes(miniatura or imagem)
    return True
