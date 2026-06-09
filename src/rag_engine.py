"""
Motor RAG (Retrieval-Augmented Generation).
TASK-008: Implementar Motor RAG (rag_engine.py)

Combina busca semântica na base de conhecimento com geração
de respostas via LLM para responder perguntas dos usuários.
"""

from typing import Optional
import logging

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from .config import AgentConfig, AGENT_SCOPE
from .knowledge_base import KnowledgeBase

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """Você é o {agent_name}, um agente de IA que auxilia a equipe {team}.

{scope}

## Instruções:
- Responda SEMPRE em português brasileiro
- Use linguagem clara e profissional
- Quando tiver documentos relevantes no contexto, baseie sua resposta neles
- Se não souber a resposta, diga "Não encontrei essa informação na base de conhecimento"
- Cite as fontes quando possível (nome do documento)
- Seja conciso mas completo

## Contexto da base de conhecimento:
{context}
"""


class RAGEngine:
    """Motor de Retrieval-Augmented Generation."""

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.from_env()
        self.kb = KnowledgeBase(self.config)

        self.llm = ChatOpenAI(
            model=self.config.openai_model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            api_key=self.config.openai_api_key,
        )
        log.info(f"RAG Engine iniciado: model={self.config.openai_model}")

    def query(self, question: str, top_k: Optional[int] = None) -> dict:
        """
        Processa uma pergunta usando RAG.

        Returns:
            dict com 'answer', 'sources', 'context_used'
        """
        # 1. Busca semântica
        results = self.kb.search(question, top_k=top_k)
        log.info(f"RAG search: '{question[:50]}...' → {len(results)} resultados")

        # 2. Montar contexto
        context_parts = []
        sources = []
        for hit in results:
            source = hit["metadata"].get("source", "desconhecido")
            context_parts.append(f"[Fonte: {source}]\n{hit['text']}")
            if source not in sources:
                sources.append(source)

        context = "\n\n---\n\n".join(context_parts) if context_parts else "Nenhum documento relevante encontrado na base."

        # 3. Gerar resposta com LLM
        system = SYSTEM_PROMPT.format(
            agent_name=self.config.name,
            team=self.config.team,
            scope=AGENT_SCOPE,
            context=context,
        )

        messages = [
            SystemMessage(content=system),
            HumanMessage(content=question),
        ]

        response = self.llm.invoke(messages)
        answer = response.content

        log.info(f"RAG response: {len(answer)} chars, {len(sources)} sources")

        return {
            "answer": answer,
            "sources": sources,
            "context_used": len(context_parts),
            "question": question,
        }

    def query_simple(self, question: str) -> str:
        """Versão simplificada que retorna apenas a resposta."""
        result = self.query(question)
        return result["answer"]

    def get_stats(self) -> dict:
        """Estatísticas do motor RAG."""
        kb_stats = self.kb.get_stats()
        return {
            "model": self.config.openai_model,
            "temperature": self.config.temperature,
            "top_k": self.config.top_k,
            "knowledge_base": kb_stats,
        }
