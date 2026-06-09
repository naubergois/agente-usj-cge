"""
Coletor de Documentação USJ/CGE.
TASK-006: Coletar Documentação USJ e CGE

Coleta e estrutura documentos de diversas fontes para alimentar
a base de conhecimento do agente.
"""

from pathlib import Path
from typing import Optional
import json
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from .config import AgentConfig, DATA_DIR, DOCS_DIR

log = logging.getLogger(__name__)


class DocumentCollector:
    """Coleta documentos de diversas fontes e converte para Markdown."""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.from_env()
        self.docs_dir = DOCS_DIR
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def collect_from_url(self, url: str, filename: Optional[str] = None) -> Path:
        """Coleta documento de URL e salva como Markdown."""
        log.info(f"Coletando: {url}")

        response = requests.get(url, timeout=30, headers={
            "User-Agent": "AgentUSJ-CGE/1.0 (DocumentCollector)"
        })
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remover scripts, styles, nav
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        # Converter para Markdown
        content = md(str(soup), heading_style="ATX", bullets="-")

        # Gerar nome de arquivo
        if not filename:
            title = soup.find("title")
            filename = (title.text.strip()[:60] if title else "documento") + ".md"
            filename = "".join(c if c.isalnum() or c in "- _." else "_" for c in filename)

        filepath = self.docs_dir / filename
        filepath.write_text(content, encoding="utf-8")
        log.info(f"Salvo: {filepath} ({len(content)} chars)")

        return filepath

    def collect_from_file(self, source: Path, category: str = "geral") -> Path:
        """Copia/converte arquivo local para a base de documentos."""
        target_dir = self.docs_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)

        if source.suffix == ".md":
            content = source.read_text(encoding="utf-8")
        elif source.suffix == ".txt":
            content = source.read_text(encoding="utf-8")
        elif source.suffix == ".pdf":
            content = self._extract_pdf(source)
        else:
            content = source.read_text(encoding="utf-8")

        target = target_dir / f"{source.stem}.md"
        target.write_text(content, encoding="utf-8")
        log.info(f"Coletado: {source.name} → {target}")

        return target

    def collect_from_text(self, text: str, filename: str, category: str = "geral") -> Path:
        """Salva texto direto como documento."""
        target_dir = self.docs_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / filename
        target.write_text(text, encoding="utf-8")
        log.info(f"Salvo texto: {target}")

        return target

    def _extract_pdf(self, path: Path) -> str:
        """Extrai texto de PDF (fallback simples)."""
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(path))
            text = ""
            for page in doc:
                text += page.get_text() + "\n\n"
            return text
        except ImportError:
            log.warning("PyMuPDF não instalado, PDF ignorado")
            return f"[PDF não processado: {path.name}]"

    def list_documents(self) -> list[dict]:
        """Lista todos os documentos coletados."""
        docs = []
        for f in sorted(self.docs_dir.rglob("*.md")):
            stat = f.stat()
            docs.append({
                "path": str(f.relative_to(DATA_DIR)),
                "name": f.name,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        return docs

    def get_stats(self) -> dict:
        """Estatísticas da coleção de documentos."""
        docs = list(self.docs_dir.rglob("*.md"))
        total_chars = sum(f.read_text(encoding="utf-8").__len__() for f in docs)
        return {
            "total_documents": len(docs),
            "total_chars": total_chars,
            "categories": list(set(f.parent.name for f in docs)),
        }
