"""
Testes da Base de Conhecimento.
TASK-016: Testes e Validação de Qualidade do Agente
"""

import pytest
from pathlib import Path
import tempfile

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.knowledge_base import KnowledgeBase
from src.config import AgentConfig


@pytest.fixture
def config():
    """Config de teste com diretório temporário."""
    return AgentConfig(
        chroma_persist_dir=tempfile.mkdtemp(),
        chroma_collection="test_collection",
        openai_api_key="test-key",
    )


@pytest.fixture
def kb(config):
    """KnowledgeBase de teste."""
    return KnowledgeBase(config)


def test_kb_init(kb):
    """Testa inicialização."""
    assert kb.collection is not None
    assert kb.collection.count() == 0


def test_chunk_text(kb):
    """Testa chunking de texto."""
    text = "A" * 3000  # Texto grande
    chunks = kb._chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= kb.config.chunk_size + 100 for c in chunks)


def test_chunk_text_small(kb):
    """Texto pequeno não é dividido."""
    text = "Texto curto"
    chunks = kb._chunk_text(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_index_and_search(kb, tmp_path):
    """Testa indexação e busca."""
    # Criar documento
    doc = tmp_path / "test.md"
    doc.write_text("A CGE é a Controladoria Geral do Estado do Ceará. "
                   "Ela é responsável pelo controle interno e transparência. "
                   "A ASESI é a assessoria de sistemas de informação da CGE.")

    # Indexar
    chunks = kb.index_document(doc, "teste")
    assert chunks > 0

    # Buscar
    results = kb.search("O que é a CGE?")
    assert len(results) > 0
    assert "CGE" in results[0]["text"] or "Controladoria" in results[0]["text"]


def test_clear(kb, tmp_path):
    """Testa limpeza da base."""
    doc = tmp_path / "clear_test.md"
    doc.write_text("Documento para teste de limpeza da base vetorial.")
    kb.index_document(doc)

    assert kb.collection.count() > 0
    kb.clear()
    assert kb.collection.count() == 0


def test_get_stats(kb):
    """Testa estatísticas."""
    stats = kb.get_stats()
    assert "collection" in stats
    assert "total_chunks" in stats
    assert stats["total_chunks"] == 0
