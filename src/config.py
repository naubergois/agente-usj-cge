"""
Configuração central do Agente USJ/CGE.
TASK-002: Definir Escopo do Agente
"""

from pathlib import Path
from pydantic import BaseModel, Field
import os

# Diretórios
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DOCS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chromadb"


class AgentConfig(BaseModel):
    """Configuração do agente colaborador."""

    # Identidade
    name: str = Field(default="Robô Nordestino Chinês")
    team: str = Field(default="USJ/ASESI/CGE")
    version: str = Field(default="0.1.0")

    # LLM
    openai_api_key: str = Field(default="")
    openai_model: str = Field(default="gpt-4o-mini")
    temperature: float = Field(default=0.3)
    max_tokens: int = Field(default=2048)

    # ChromaDB
    chroma_persist_dir: str = Field(default=str(CHROMA_DIR))
    chroma_collection: str = Field(default="usj_cge_knowledge")

    # RAG
    chunk_size: int = Field(default=1000)
    chunk_overlap: int = Field(default=200)
    top_k: int = Field(default=5)

    # Streamlit
    streamlit_port: int = Field(default=8501)

    # WhatsApp
    wacli_device_id: str = Field(default="")
    wacli_sync_dir: str = Field(default=str(DATA_DIR / "whatsapp"))

    @classmethod
    def from_env(cls) -> "AgentConfig":
        """Carrega configuração do .env."""
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", str(CHROMA_DIR)),
            chroma_collection=os.getenv("CHROMA_COLLECTION", "usj_cge_knowledge"),
            streamlit_port=int(os.getenv("STREAMLIT_PORT", "8501")),
            wacli_device_id=os.getenv("WACLI_DEVICE_ID", ""),
            wacli_sync_dir=os.getenv("WACLI_SYNC_DIR", str(DATA_DIR / "whatsapp")),
        )


# Escopo do Agente (TASK-002)
AGENT_SCOPE = """
## Escopo do Agente Colaborador USJ/CGE

### O que o agente FAZ:
- Responde perguntas sobre documentação interna da USJ, ASESI e CGE
- Busca informações em portarias, resoluções, manuais e notas técnicas
- Auxilia na redação de documentos baseado em templates existentes
- Fornece resumos de reuniões e decisões anteriores
- Orienta sobre procedimentos e fluxos internos

### O que o agente NÃO FAZ:
- Não toma decisões administrativas
- Não acessa sistemas externos sem autorização
- Não divulga informações sigilosas fora do escopo autorizado
- Não substitui a análise humana em decisões críticas

### Público-alvo:
- Servidores da ASESI (Assessoria Especial de Sistemas de Informação)
- Equipe da CGE (Controladoria Geral do Estado)
- Equipe da USJ (Universidade São José)

### Fontes de dados:
- Documentação interna (Markdown, PDF)
- Portarias e resoluções
- Atas de reuniões
- Manuais de procedimentos
- Base de conhecimento vetorial (ChromaDB)
"""
