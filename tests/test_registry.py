import pytest

from fluig_support_ia.tools.registry import Tool, ToolRegistry, ToolResult


async def _ok_handler(valor: str = "x") -> ToolResult:
    return ToolResult(ok=True, summary=f"recebi {valor}", data={"valor": valor})


async def _boom_handler() -> ToolResult:
    raise RuntimeError("conexao recusada")


def _tool(name: str, handler) -> Tool:
    return Tool(
        name=name,
        description="ferramenta de teste",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=handler,
    )


def test_registra_e_lista_ferramentas():
    registry = ToolRegistry()
    registry.register(_tool("alpha", _ok_handler))
    registry.register(_tool("beta", _boom_handler))
    assert registry.names == ["alpha", "beta"]


def test_nome_duplicado_e_rejeitado():
    registry = ToolRegistry()
    registry.register(_tool("alpha", _ok_handler))
    with pytest.raises(ValueError, match="duplicada"):
        registry.register(_tool("alpha", _ok_handler))


def test_schema_segue_o_formato_da_openai():
    registry = ToolRegistry()
    registry.register(_tool("alpha", _ok_handler))
    schema = registry.schemas()[0]
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "alpha"
    assert schema["function"]["parameters"]["type"] == "object"


async def test_executa_com_sucesso():
    registry = ToolRegistry()
    registry.register(_tool("alpha", _ok_handler))
    result = await registry.execute("alpha", {"valor": "42"})
    assert result.ok
    assert result.data == {"valor": "42"}


async def test_ferramenta_desconhecida_volta_como_falha():
    result = await ToolRegistry().execute("nao_existe", {})
    assert not result.ok
    assert "desconhecida" in result.summary


async def test_excecao_do_handler_nao_propaga():
    registry = ToolRegistry()
    registry.register(_tool("boom", _boom_handler))
    result = await registry.execute("boom", {})
    assert not result.ok
    assert "conexao recusada" in result.summary


async def test_parametro_inesperado_volta_como_falha():
    registry = ToolRegistry()
    registry.register(_tool("alpha", _ok_handler))
    result = await registry.execute("alpha", {"campo_inventado": 1})
    assert not result.ok
    assert "nao suportados" in result.summary
