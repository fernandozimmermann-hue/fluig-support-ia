import pytest

from fluig_support_ia.knowledge.chunking import chunk_text


def test_texto_vazio_nao_gera_trecho():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_texto_curto_gera_um_unico_trecho():
    chunks = chunk_text("Erro ao publicar o processo.", max_chars=200)
    assert len(chunks) == 1
    assert chunks[0].text == "Erro ao publicar o processo."
    assert chunks[0].index == 0


def test_respeita_o_tamanho_maximo_ignorando_a_sobreposicao():
    texto = "\n\n".join(f"Paragrafo numero {i} com algum conteudo tecnico." * 3 for i in range(12))
    max_chars = 300
    overlap = 50
    chunks = chunk_text(texto, max_chars=max_chars, overlap=overlap)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= max_chars + overlap + 2


def test_indices_sao_sequenciais():
    texto = "\n\n".join(f"Bloco {i} " * 30 for i in range(8))
    chunks = chunk_text(texto, max_chars=250, overlap=40)
    assert [c.index for c in chunks] == list(range(len(chunks)))


def test_sobreposicao_repete_o_fim_do_trecho_anterior():
    texto = "A" * 200 + "\n\n" + "B" * 200
    chunks = chunk_text(texto, max_chars=250, overlap=30)
    assert len(chunks) == 2
    assert chunks[1].text.startswith("A" * 30)


def test_sem_sobreposicao_os_trechos_nao_se_repetem():
    texto = "A" * 200 + "\n\n" + "B" * 200
    chunks = chunk_text(texto, max_chars=250, overlap=0)
    assert chunks[1].text == "B" * 200


def test_frase_unica_maior_que_o_limite_e_cortada():
    chunks = chunk_text("X" * 1000, max_chars=300, overlap=0)
    assert len(chunks) >= 4
    assert all(len(c.text) <= 300 for c in chunks)


@pytest.mark.parametrize(("max_chars", "overlap"), [(0, 0), (100, 100), (100, -1)])
def test_parametros_invalidos_falham(max_chars, overlap):
    with pytest.raises(ValueError):
        chunk_text("texto qualquer", max_chars=max_chars, overlap=overlap)
