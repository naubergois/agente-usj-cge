"""
Base de Conhecimento com ChromaDB.
TASK-007: Criar Base de Conhecimento com ChromaDB

Indexa documentos coletados em vetores para busca semântica (RAG).
"""

from pathlib import Path
from typing import Optional
import hashlib
import logging

import chromadb
from chromadb.config import Settings

from .config import AgentConfig, CHROMA_DIR, DOCS_DIR

log = logging.getLogger(__name__)


class KnowledgeBase:
    """Base de conhecimento vetorial usando ChromaDB."""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.from_env()

        persist_dir = Path(self.config.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=self.config.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        log.info(f"ChromaDB: collection='{self.config.chroma_collection}' docs={self.collection.count()}")

    def _chunk_text(self, text: str) -> list[str]:
        """Divide texto em chunks com overlap."""
        chunks = []
        size = self.config.chunk_size
        overlap = self.config.chunk_overlap

        if len(text) <= size:
            return [text]

        start = 0
        while start < len(text):
            end = start + size
            chunk = text[start:end]

            # Tentar cortar no fim de uma frase
            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                cut = max(last_period, last_newline)
                if cut > size * 0.5:
                    chunk = chunk[: cut + 1]
                    end = start + cut + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if len(c) > 50]

    def _doc_id(self, text: str, source: str) -> str:
        """Gera ID único para um chunk."""
        h = hashlib.md5(f"{source}:{text[:100]}".encode()).hexdigest()[:12]
        return f"{source}_{h}"

    def index_document(self, filepath: Path, category: str = "geral") -> int:
        """Indexa um documento na base vetorial."""
        text = filepath.read_text(encoding="utf-8")
        chunks = self._chunk_text(text)

        if not chunks:
            log.warning(f"Documento vazio: {filepath}")
            return 0

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            doc_id = self._doc_id(chunk, filepath.stem)
            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append({
                "source": filepath.name,
                "category": category,
                "chunk_index": i,
                "total_chunks": len(chunks),
            })

        self.collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        log.info(f"Indexado: {filepath.name} → {len(chunks)} chunks")
        return len(chunks)

    def index_all_documents(self) -> dict:
        """Indexa todos os documentos do diretório data/documents."""
        total = 0
        indexed = 0

        for doc in sorted(DOCS_DIR.rglob("*.md")):
            category = doc.parent.name if doc.parent != DOCS_DIR else "geral"
            chunks = self.index_document(doc, category)
            total += chunks
            indexed += 1

        log.info(f"Indexação completa: {indexed} docs, {total} chunks")
        return {"documents": indexed, "chunks": total}

    def search(self, query: str, top_k: Optional[int] = None) -> list[dict]:
        """Busca semântica na base de conhecimento."""
        k = top_k or self.config.top_k

        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                hits.append({
                    "text": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0,
                    "score": 1 - (results["distances"][0][i] if results["distances"] else 0),
                })

        return hits

    def get_stats(self) -> dict:
        """Estatísticas da base vetorial."""
        return {
            "collection": self.config.chroma_collection,
            "total_chunks": self.collection.count(),
            "persist_dir": self.config.chroma_persist_dir,
        }

    def clear(self) -> None:
        """Limpa a coleção (usar com cuidado)."""
        self.client.delete_collection(self.config.chroma_collection)
        self.collection = self.client.get_or_create_collection(
            name=self.config.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("Base vetorial limpa")
