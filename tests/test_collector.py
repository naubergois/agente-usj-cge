"""
Testes do Coletor de Documentos.
TASK-016: Testes e Validação de Qualidade do Agente
"""

import pytest
from pathlib import Path
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collector import DocumentCollector
from src.config import AgentConfig


@pytest.fixture
def config():
    """Config de teste."""
    return AgentConfig(
        chroma_persist_dir=tempfile.mkdtemp(),
        openai_api_key="test-key",
    )


@pytest.fixture
def collector(config):
    """Collector de teste."""
    return DocumentCollector(config)


def test_collect_from_text(collector):
    """Testa coleta de texto direto."""
    text = "# Documento de Teste\n\nConteúdo de exemplo para o agente USJ/CGE."
    path = collector.collect_from_text(text, "teste.md", "testes")

    assert path.exists()
    assert path.read_text() == text
    assert "testes" in str(path)


def test_collect_from_text_creates_dirs(collector):
    """Testa criação automática de diretórios."""
    text = "Conteúdo"
    path = collector.collect_from_text(text, "novo.md", "nova_categoria")

    assert path.exists()
    assert path.parent.name == "nova_categoria"


def test_list_documents(collector):
    """Testa listagem de documentos."""
    collector.collect_from_text("Doc 1", "doc1.md", "cat1")
    collector.collect_from_text("Doc 2", "doc2.md", "cat2")

    docs = collector.list_documents()
    assert len(docs) >= 2


def test_get_stats(collector):
    """Testa estatísticas."""
    collector.collect_from_text("Conteúdo de teste", "stats_test.md")

    stats = collector.get_stats()
    assert stats["total_documents"] >= 1
    assert stats["total_chars"] > 0
