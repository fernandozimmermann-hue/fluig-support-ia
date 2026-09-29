import pytest

from fluig_support_ia.knowledge.loaders import load_directory, load_file, parse_front_matter


def test_front_matter_extrai_titulo_e_url():
    meta, corpo = parse_front_matter(
        "---\ntitle: Processo travado\nurl: https://tdn\n---\nConteudo"
    )
    assert meta == {"title": "Processo travado", "url": "https://tdn"}
    assert corpo == "Conteudo"


def test_texto_sem_front_matter_fica_intacto():
    meta, corpo = parse_front_matter("# Titulo\nConteudo")
    assert meta == {}
    assert corpo == "# Titulo\nConteudo"


def test_front_matter_sem_fechamento_nao_e_consumido():
    texto = "---\ntitle: X\nConteudo sem fechar"
    meta, corpo = parse_front_matter(texto)
    assert meta == {}
    assert corpo == texto


def test_load_file_usa_o_nome_do_arquivo_como_titulo_padrao(tmp_path):
    caminho = tmp_path / "erro-de-dataset.md"
    caminho.write_text("Passo a passo.", encoding="utf-8")
    documento = load_file(caminho, root=tmp_path)
    assert documento is not None
    assert documento.title == "erro de dataset"
    assert documento.source == "erro-de-dataset.md"


def test_load_file_ignora_arquivo_vazio(tmp_path):
    caminho = tmp_path / "vazio.md"
    caminho.write_text("   \n", encoding="utf-8")
    assert load_file(caminho, root=tmp_path) is None


def test_load_directory_percorre_subpastas_e_filtra_extensoes(tmp_path):
    (tmp_path / "bpm").mkdir()
    (tmp_path / "bpm" / "a.md").write_text("conteudo a", encoding="utf-8")
    (tmp_path / "b.txt").write_text("conteudo b", encoding="utf-8")
    (tmp_path / "ignorar.pdf").write_text("conteudo c", encoding="utf-8")

    documentos = load_directory(tmp_path)
    fontes = sorted(documento.source for documento in documentos)
    assert fontes == ["b.txt", "bpm/a.md"]


def test_load_directory_falha_se_o_diretorio_nao_existe(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_directory(tmp_path / "nao-existe")
