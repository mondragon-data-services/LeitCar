"""Tratamento das fotos do portfolio.

Foto de celular chega com 4000 px e varios MB. O que a galeria serve tem
que ser bem menor, com a orientacao do EXIF ja aplicada — senao o cliente
no 4G desiste antes de ver o trabalho.
"""
from __future__ import annotations

import io

import pytest

from servicos import portfolio


def imagem(largura: int = 4000, altura: int = 3000, cor=(20, 40, 90)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (largura, altura), cor).save(buf, "JPEG", quality=92)
    return buf.getvalue()


@pytest.fixture
def limpar():
    criados: list[str] = []
    yield criados
    for arquivo in criados:
        portfolio.remover(arquivo)


def test_foto_grande_e_reduzida_e_ganha_miniatura(limpar):
    from PIL import Image

    arquivo = portfolio.salvar(imagem(), "IMG_4021.JPEG")
    limpar.append(arquivo)

    grande = Image.open(portfolio.caminho(arquivo))
    thumb = Image.open(portfolio.caminho_thumb(arquivo))
    assert max(grande.size) == portfolio.LARGURA_MAX
    assert max(thumb.size) == portfolio.LARGURA_THUMB
    assert portfolio.caminho(arquivo).stat().st_size < 600 * 1024


def test_nome_vem_do_conteudo_entao_a_mesma_foto_nao_duplica(limpar):
    dados = imagem(1200, 900, (80, 20, 30))
    a = portfolio.salvar(dados, "foto.jpg")
    b = portfolio.salvar(dados, "foto.jpg")
    limpar.append(a)
    assert a == b

    # conteudo diferente, nome de arquivo igual: precisa gerar outro nome
    c = portfolio.salvar(imagem(1200, 900, (10, 90, 40)), "foto.jpg")
    limpar.append(c)
    assert c != a


def test_nome_de_arquivo_do_whatsapp_vira_slug(limpar):
    arquivo = portfolio.salvar(imagem(800, 600),
                               "WhatsApp Image 2026-09-01 at 12.10.41 (1).jpeg")
    limpar.append(arquivo)
    assert arquivo.startswith("whatsapp-image-2026-09-01-at-12-10-41-1-")
    assert arquivo.endswith(".jpg")


def test_orientacao_do_exif_e_aplicada(limpar):
    """Foto tirada com o celular deitado nao pode sair de lado na galeria."""
    from PIL import Image

    exif = Image.Exif()
    exif[274] = 6                       # orientation: girar 90 graus
    buf = io.BytesIO()
    Image.new("RGB", (800, 400), (60, 60, 60)).save(buf, "JPEG", exif=exif)

    arquivo = portfolio.salvar(buf.getvalue(), "deitada.jpg")
    limpar.append(arquivo)
    assert Image.open(portfolio.caminho(arquivo)).size == (400, 800)


def test_arquivo_que_nao_e_imagem_e_recusado():
    with pytest.raises(portfolio.ImagemInvalida):
        portfolio.salvar(b"isto nao e uma imagem", "curriculo.pdf")
    with pytest.raises(portfolio.ImagemInvalida):
        portfolio.salvar(b"", "vazio.jpg")


def test_remover_apaga_original_e_miniatura():
    arquivo = portfolio.salvar(imagem(600, 400, (5, 5, 5)), "descartavel.jpg")
    assert portfolio.existe(arquivo)
    portfolio.remover(arquivo)
    assert not portfolio.caminho(arquivo).exists()
    assert not portfolio.caminho_thumb(arquivo).exists()


def test_bytes_de_cai_para_o_original_quando_nao_ha_miniatura(limpar):
    arquivo = portfolio.salvar(imagem(900, 600, (30, 30, 60)), "sem-thumb.jpg")
    limpar.append(arquivo)
    portfolio.caminho_thumb(arquivo).unlink()
    assert portfolio.bytes_de(arquivo, thumb=True)
    assert portfolio.bytes_de("nao-existe.jpg") is None
