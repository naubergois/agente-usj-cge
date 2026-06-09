"""
Testes do Motor RAG.
TASK-016: Testes e Validação de Qualidade do Agente
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rag_engine import RAGEngine
from src.config import AgentConfig


@pytest.fixture
def config():
    """Config de teste."""
    return AgentConfig(
        chroma_persist_dir=tempfile.mkdtemp(),
        chroma_collection="test_rag",
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
    )


def test_rag_engine_init(config):
    """Testa inicialização do RAG."""
    with patch("src.rag_engine.ChatOpenAI"):
        engine = RAGEngine(config)
        assert engine.config.openai_model == "gpt-4o-mini"
        assert engine.kb is not None


def test_rag_query_with_mock(config):
    """Testa query RAG com LLM mockado."""
    with patch("src.rag_engine.ChatOpenAI") as mock_llm_class:
        mock_response = MagicMock()
        mock_response.content = "A CGE é a Controladoria Geral do Estado."
        mock_llm_class.return_value.invoke.return_value = mock_response

        engine = RAGEngine(config)
        result = engine.query("O que é a CGE?")

        assert "answer" in result
        assert "sources" in result
        assert "context_used" in result
        assert result["answer"] == "A CGE é a Controladoria Geral do Estado."


def test_rag_get_stats(config):
    """Testa estatísticas do RAG."""
    with patch("src.rag_engine.ChatOpenAI"):
        engine = RAGEngine(config)
        stats = engine.get_stats()

        assert "model" in stats
        assert "knowledge_base" in stats
        assert stats["model"] == "gpt-4o-mini"
