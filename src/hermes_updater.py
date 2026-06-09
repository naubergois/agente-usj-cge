"""
Agente Hermes — Atualização Automática da Base.
TASK-011: Criar Agente Hermes para Atualização Automática

Daemon que monitora novas fontes de dados e atualiza a base
de conhecimento automaticamente.
"""

import time
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from .config import AgentConfig, DOCS_DIR
from .collector import DocumentCollector
from .knowledge_base import KnowledgeBase

log = logging.getLogger(__name__)


class HermesUpdater:
    """
    Agente Hermes — monitora e atualiza a base de conhecimento.

    Funcionalidades:
    - Monitora diretório de documentos para novos arquivos
    - Re-indexa documentos modificados
    - Coleta periódica de URLs configuradas
    - Log de atualizações
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.from_env()
        self.collector = DocumentCollector(self.config)
        self.kb = KnowledgeBase(self.config)
        self.watch_dir = DOCS_DIR
        self.interval_seconds = 300  # 5 minutos
        self.known_files: dict[str, float] = {}  # path -> mtime
        self._running = False

        # URLs para coleta periódica
        self.watch_urls: list[dict] = []

    def scan_changes(self) -> list[Path]:
        """Verifica novos/modificados documentos."""
        changed = []

        for doc in self.watch_dir.rglob("*.md"):
            path_str = str(doc)
            mtime = doc.stat().st_mtime

            if path_str not in self.known_files or self.known_files[path_str] < mtime:
                changed.append(doc)
                self.known_files[path_str] = mtime

        return changed

    def update_once(self) -> dict:
        """Executa um ciclo de atualização."""
        changed = self.scan_changes()
        indexed = 0

        for doc in changed:
            category = doc.parent.name if doc.parent != DOCS_DIR else "geral"
            chunks = self.kb.index_document(doc, category)
            indexed += chunks
            log.info(f"Hermes: atualizado {doc.name} ({chunks} chunks)")

        return {
            "timestamp": datetime.now().isoformat(),
            "files_changed": len(changed),
            "chunks_indexed": indexed,
        }

    def collect_urls(self) -> int:
        """Coleta URLs configuradas."""
        collected = 0
        for entry in self.watch_urls:
            try:
                self.collector.collect_from_url(entry["url"], entry.get("filename"))
                collected += 1
            except Exception as e:
                log.error(f"Hermes: falha ao coletar {entry['url']}: {e}")
        return collected

    def run_daemon(self) -> None:
        """Executa como daemon (loop infinito)."""
        log.info(f"Hermes daemon iniciado (intervalo: {self.interval_seconds}s)")
        self._running = True

        # Scan inicial
        self.update_once()

        while self._running:
            time.sleep(self.interval_seconds)
            try:
                result = self.update_once()
                if result["files_changed"] > 0:
                    log.info(f"Hermes: {result['files_changed']} atualizações, {result['chunks_indexed']} chunks")

                # Coleta periódica de URLs
                if self.watch_urls:
                    collected = self.collect_urls()
                    if collected:
                        self.update_once()  # Re-indexar após coleta
            except Exception as e:
                log.error(f"Hermes error: {e}")

    def stop(self) -> None:
        """Para o daemon."""
        self._running = False
        log.info("Hermes daemon parado")

    def add_watch_url(self, url: str, filename: Optional[str] = None) -> None:
        """Adiciona URL para monitoramento."""
        self.watch_urls.append({"url": url, "filename": filename})

    def get_status(self) -> dict:
        """Status do Hermes."""
        return {
            "running": self._running,
            "known_files": len(self.known_files),
            "watch_urls": len(self.watch_urls),
            "interval_seconds": self.interval_seconds,
            "kb_stats": self.kb.get_stats(),
        }
