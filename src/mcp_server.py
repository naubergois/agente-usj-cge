"""
Servidor MCP local com FastMCP.
Expõe todas as funcionalidades do Agente USJ/CGE como ferramentas MCP.

Ferramentas expostas:
  - chat: Conversa com o agente (RAG + memória)
  - search_knowledge: Busca semântica na base de conhecimento
  - index_documents: Indexa todos os documentos
  - list_documents: Lista documentos da base
  - summarize: Resume um texto
  - draft_document: Auxilia na redação de documentos
  - collect_url: Coleta documento de URL
  - hermes_update: Executa atualização da base (Hermes)
  - agent_status: Status geral do agente e base

Uso:
  fastmcp run src/mcp_server.py
  python -m src.mcp_server
"""

from fastmcp import FastMCP

from .config import AgentConfig
from .agent import ConversationalAgent
from .knowledge_base import KnowledgeBase
from .collector import DocumentCollector
from .hermes_updater import HermesUpdater
from .rag_engine import RAGEngine

# ─── Inicialização ────────────────────────────────────────────

config = AgentConfig.from_env()

mcp = FastMCP(
    "Agente USJ/CGE — Robô Nordestino Chinês",
    instructions=(
        "Servidor MCP do Agente Colaborador USJ/CGE. "
        "Responde perguntas sobre documentação interna da USJ, ASESI e CGE, "
        "busca informações em portarias, resoluções e manuais, "
        "auxilia na redação de documentos e orienta sobre procedimentos."
    ),
)

# Instâncias lazy (criadas no primeiro uso)
_agent: ConversationalAgent | None = None
_kb: KnowledgeBase | None = None
_collector: DocumentCollector | None = None
_hermes: HermesUpdater | None = None
_rag: RAGEngine | None = None


def _get_agent() -> ConversationalAgent:
    global _agent
    if _agent is None:
        _agent = ConversationalAgent(config)
    return _agent


def _get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase(config)
    return _kb


def _get_collector() -> DocumentCollector:
    global _collector
    if _collector is None:
        _collector = DocumentCollector(config)
    return _collector


def _get_hermes() -> HermesUpdater:
    global _hermes
    if _hermes is None:
        _hermes = HermesUpdater(config)
    return _hermes


def _get_rag() -> RAGEngine:
    global _rag
    if _rag is None:
        _rag = RAGEngine(config)
    return _rag


# ─── Ferramentas MCP ─────────────────────────────────────────


@mcp.tool
def chat(message: str, user: str = "mcp-client") -> dict:
    """
    Conversa com o Agente USJ/CGE (Robô Nordestino Chinês).

    Usa RAG para buscar contexto na base de conhecimento e mantém
    memória de conversa entre chamadas.

    Args:
        message: Mensagem ou pergunta do usuário.
        user: Identificador do usuário (opcional).

    Returns:
        Resposta do agente com fontes utilizadas.
    """
    agent = _get_agent()
    result = agent.chat(message, user=user)
    return {
        "response": result["response"],
        "sources": result["sources"],
        "context_used": result["context_used"],
    }


@mcp.tool
def search_knowledge(query: str, top_k: int = 5) -> list[dict]:
    """
    Busca semântica na base de conhecimento vetorial (ChromaDB).

    Retorna os trechos mais relevantes encontrados nos documentos
    indexados, sem gerar resposta via LLM.

    Args:
        query: Texto de busca.
        top_k: Quantidade de resultados (padrão: 5).

    Returns:
        Lista de trechos relevantes com metadados e score.
    """
    kb = _get_kb()
    results = kb.search(query, top_k=top_k)
    return [
        {
            "text": hit["text"][:500],
            "source": hit["metadata"].get("source", "desconhecido"),
            "category": hit["metadata"].get("category", "geral"),
            "score": round(hit["score"], 4),
        }
        for hit in results
    ]


@mcp.tool
def index_documents() -> dict:
    """
    Indexa (ou re-indexa) todos os documentos do diretório data/documents
    na base vetorial ChromaDB.

    Returns:
        Estatísticas da indexação (documentos e chunks processados).
    """
    kb = _get_kb()
    result = kb.index_all_documents()
    return {
        "status": "ok",
        "documents_indexed": result["documents"],
        "chunks_created": result["chunks"],
        "total_in_base": kb.collection.count(),
    }


@mcp.tool
def list_documents() -> list[dict]:
    """
    Lista todos os documentos Markdown coletados na pasta data/documents.

    Returns:
        Lista com nome, caminho, tamanho e data de modificação.
    """
    collector = _get_collector()
    return collector.list_documents()


@mcp.tool
def summarize(text: str) -> str:
    """
    Resume um texto usando o LLM do agente.

    Args:
        text: Texto a ser resumido (máx ~8000 caracteres serão usados).

    Returns:
        Resumo em português.
    """
    agent = _get_agent()
    return agent.summarize_document(text)


@mcp.tool
def draft_document(description: str, doc_type: str = "ofício") -> str:
    """
    Auxilia na redação de documentos oficiais.

    Gera um rascunho baseado na descrição fornecida.

    Args:
        description: Descrição do que o documento deve conter.
        doc_type: Tipo do documento (ofício, memorando, nota técnica, etc).

    Returns:
        Rascunho do documento em português formal.
    """
    agent = _get_agent()
    return agent.help_draft(description, doc_type=doc_type)


@mcp.tool
def collect_url(url: str, filename: str | None = None) -> dict:
    """
    Coleta documento de uma URL e salva como Markdown na base.

    Converte HTML para Markdown e armazena em data/documents/.

    Args:
        url: URL da página a coletar.
        filename: Nome do arquivo (gerado automaticamente se omitido).

    Returns:
        Caminho do arquivo salvo e tamanho.
    """
    collector = _get_collector()
    filepath = collector.collect_from_url(url, filename=filename)
    return {
        "status": "ok",
        "path": str(filepath),
        "filename": filepath.name,
        "size_chars": filepath.stat().st_size,
    }


@mcp.tool
def collect_text(text: str, filename: str, category: str = "geral") -> dict:
    """
    Salva um texto diretamente como documento na base de conhecimento.

    Args:
        text: Conteúdo do documento em Markdown.
        filename: Nome do arquivo (ex: 'procedimento-xyz.md').
        category: Categoria/subpasta (ex: 'procedimentos', 'reunioes').

    Returns:
        Caminho do arquivo salvo.
    """
    collector = _get_collector()
    filepath = collector.collect_from_text(text, filename, category=category)
    return {
        "status": "ok",
        "path": str(filepath),
        "filename": filepath.name,
    }


@mcp.tool
def hermes_update() -> dict:
    """
    Executa um ciclo do Agente Hermes — verifica novos/modificados
    documentos e atualiza a base vetorial.

    Returns:
        Resultado da atualização (arquivos alterados, chunks indexados).
    """
    hermes = _get_hermes()
    return hermes.update_once()


@mcp.tool
def agent_status() -> dict:
    """
    Retorna status geral do agente, base de conhecimento e configuração.

    Returns:
        Informações sobre o agente, modelo LLM, base vetorial e documentos.
    """
    kb = _get_kb()
    collector = _get_collector()

    return {
        "agent": {
            "name": config.name,
            "team": config.team,
            "version": config.version,
            "model": config.openai_model,
            "temperature": config.temperature,
        },
        "knowledge_base": kb.get_stats(),
        "documents": collector.get_stats(),
    }


@mcp.tool
def reset_conversation() -> dict:
    """
    Limpa o histórico de conversa do agente.
    Útil para iniciar um novo contexto de conversa.

    Returns:
        Confirmação do reset.
    """
    agent = _get_agent()
    agent.reset()
    return {"status": "ok", "message": "Histórico de conversa limpo."}


@mcp.tool
def get_conversation_history() -> list[dict]:
    """
    Retorna o histórico de conversa atual do agente.

    Returns:
        Lista de mensagens (role, content, timestamp).
    """
    agent = _get_agent()
    return agent.get_history()


# ─── Entrypoint ───────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
