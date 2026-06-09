"""
Interface Web com Streamlit.
TASK-009: Criar Interface Web (Streamlit)

Interface conversacional para interagir com o Agente USJ/CGE.
"""

import streamlit as st
from pathlib import Path
import sys

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import ConversationalAgent
from src.config import AgentConfig
from src.knowledge_base import KnowledgeBase
from src.collector import DocumentCollector


def init_agent():
    """Inicializa o agente (cached)."""
    if "agent" not in st.session_state:
        config = AgentConfig.from_env()
        st.session_state.agent = ConversationalAgent(config)
        st.session_state.config = config
    return st.session_state.agent


def main():
    st.set_page_config(
        page_title="Robô Nordestino Chinês · USJ/CGE",
        page_icon="🤖",
        layout="wide",
    )

    # Header
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown("# 🤖")
    with col2:
        st.title("Robô Nordestino Chinês")
        st.caption("Agente Colaborador USJ/ASESI/CGE · Powered by RAG + LangChain")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configurações")

        # Status
        agent = init_agent()
        config = st.session_state.config

        st.success(f"✅ Modelo: {config.openai_model}")

        kb = KnowledgeBase(config)
        stats = kb.get_stats()
        st.info(f"📚 Base: {stats['total_chunks']} chunks")

        st.divider()

        # Ações
        st.subheader("📋 Ações")

        if st.button("🗑️ Limpar conversa"):
            agent.reset()
            st.session_state.messages = []
            st.rerun()

        if st.button("📊 Reindexar base"):
            with st.spinner("Indexando documentos..."):
                result = kb.index_all_documents()
                st.success(f"✅ {result['documents']} docs, {result['chunks']} chunks")

        st.divider()

        # Upload de documentos
        st.subheader("📄 Adicionar Documento")
        uploaded = st.file_uploader("Upload (.md, .txt)", type=["md", "txt"])
        if uploaded:
            collector = DocumentCollector(config)
            content = uploaded.read().decode("utf-8")
            path = collector.collect_from_text(content, uploaded.name, "uploads")
            kb.index_document(path, "uploads")
            st.success(f"✅ {uploaded.name} indexado!")

    # Chat interface
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Exibir histórico
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                st.caption(f"📚 Fontes: {', '.join(msg['sources'])}")

    # Input
    if prompt := st.chat_input("Pergunte algo sobre USJ, ASESI ou CGE..."):
        # Mensagem do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Resposta do agente
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                result = agent.chat(prompt)

            st.markdown(result["response"])
            if result["sources"]:
                st.caption(f"📚 Fontes: {', '.join(result['sources'])}")

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["response"],
            "sources": result["sources"],
        })


if __name__ == "__main__":
    main()
