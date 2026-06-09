"""
Agente Conversacional com LangChain.
TASK-001: Desenvolver Agente Colaborador USJ e CGE
TASK-003: Desenvolvimento das Funcionalidades do Agente
TASK-015: Implementar Agente Conversacional com LangChain

Agente principal com memória de conversa, ferramentas e RAG integrado.
"""

from typing import Optional
import logging
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from .config import AgentConfig, AGENT_SCOPE
from .rag_engine import RAGEngine

log = logging.getLogger(__name__)


class ConversationalAgent:
    """
    Agente conversacional com memória e RAG.

    Funcionalidades (TASK-003):
    - Memória de conversa (últimas N mensagens)
    - Busca na base de conhecimento (RAG)
    - Resumo de documentos
    - Auxílio na redação
    - Orientação sobre procedimentos
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.from_env()
        self.rag = RAGEngine(self.config)
        self.history: list[dict] = []
        self.max_history = 20

        self.llm = ChatOpenAI(
            model=self.config.openai_model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=self.config.openai_api_key,
        )

        log.info(f"Agente '{self.config.name}' iniciado")

    def chat(self, message: str, user: str = "usuario") -> dict:
        """
        Processa mensagem do usuário.

        Returns:
            dict com 'response', 'sources', 'timestamp'
        """
        timestamp = datetime.now().isoformat()

        # Buscar contexto via RAG
        rag_result = self.rag.query(message)

        # Montar mensagens com histórico
        messages = [
            SystemMessage(content=self._build_system_prompt(rag_result)),
        ]

        # Adicionar histórico
        for entry in self.history[-self.max_history:]:
            if entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
            else:
                messages.append(AIMessage(content=entry["content"]))

        # Mensagem atual
        messages.append(HumanMessage(content=message))

        # Gerar resposta
        response = self.llm.invoke(messages)
        answer = response.content

        # Salvar no histórico
        self.history.append({"role": "user", "content": message, "user": user, "timestamp": timestamp})
        self.history.append({"role": "assistant", "content": answer, "timestamp": timestamp})

        # Limitar histórico
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

        return {
            "response": answer,
            "sources": rag_result["sources"],
            "context_used": rag_result["context_used"],
            "timestamp": timestamp,
            "user": user,
        }

    def _build_system_prompt(self, rag_result: dict) -> str:
        """Constrói o prompt do sistema com contexto RAG."""
        context_info = ""
        if rag_result["sources"]:
            context_info = f"\n\nDocumentos relevantes encontrados: {', '.join(rag_result['sources'])}"
            context_info += f"\n\nContexto:\n{rag_result['answer']}"

        return f"""Você é o {self.config.name}, agente de IA da equipe {self.config.team}.

{AGENT_SCOPE}

## Regras de conversa:
- Responda em português brasileiro
- Seja profissional mas amigável
- Use o contexto da base de conhecimento quando disponível
- Se não tiver certeza, peça mais detalhes
- Mantenha coerência com o histórico da conversa
{context_info}

Data/hora atual: {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

    def reset(self) -> None:
        """Limpa o histórico de conversa."""
        self.history = []
        log.info("Histórico limpo")

    def get_history(self) -> list[dict]:
        """Retorna o histórico de conversa."""
        return self.history.copy()

    def summarize_document(self, text: str) -> str:
        """Resume um documento."""
        messages = [
            SystemMessage(content="Você é um assistente que resume documentos de forma clara e concisa em português."),
            HumanMessage(content=f"Resuma o seguinte documento:\n\n{text[:8000]}"),
        ]
        response = self.llm.invoke(messages)
        return response.content

    def help_draft(self, description: str, doc_type: str = "ofício") -> str:
        """Auxilia na redação de documentos."""
        messages = [
            SystemMessage(content=f"Você é um assistente especializado em redigir documentos oficiais ({doc_type}) em português formal."),
            HumanMessage(content=f"Crie um rascunho de {doc_type} com base na seguinte descrição:\n\n{description}"),
        ]
        response = self.llm.invoke(messages)
        return response.content
