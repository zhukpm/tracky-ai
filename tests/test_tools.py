from typing import Annotated

from trackyai.agent.tools import tool_registry, tool
import pytest


def test_registry():

    @tool
    async def test_f(a: Annotated[int, 'a description']):
        """ function description """
        return a

    assert 'test_f' in tool_registry
    assert test_f in tool_registry
    assert tool_registry[test_f] in tool_registry
    assert tool_registry[test_f] in tool_registry.get()
    assert tool_registry[test_f] in tool_registry.get('main')
    assert 'missing tool' not in tool_registry

    t = tool_registry[test_f]
    assert not t.is_terminating()
    assert t.name == 'test_f'
    assert len(t.arguments) == 1
    assert 'function description' in t.description
    assert 'a description' in t.arguments[0].description
    assert 'a' == t.arguments[0].name

    with pytest.raises(KeyError):
        _ = tool_registry['missing-tool']

    @tool(terminating=True, scopes=['main', 'other'])
    async def test_g(b: Annotated[int, 'b description']):
        """ function description """
        return b

    assert 'test_g' in tool_registry
    assert tool_registry[test_g] in tool_registry.get('main')
    assert tool_registry[test_g] in tool_registry.get('other')
    assert tool_registry[test_g] in tool_registry.get('main', 'other')
    assert tool_registry[test_g] in tool_registry.get(test_g)
    assert tool_registry[test_g] in tool_registry.get('test_g')
    assert tool_registry[test_f] not in tool_registry.get('other')

    with pytest.raises(ValueError):
        @tool
        async def test_f(a: Annotated[int, 'a description']):
            """ function description """
            return a

    with pytest.raises(ValueError):
        @tool
        async def test_h(a: int):
            return a

    with pytest.raises(ValueError):
        @tool
        def test_h(a: Annotated[int, 'a description']):
            return a
