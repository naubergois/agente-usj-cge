"""
Integração com WhatsApp via wacli.
TASK-010: Integrar com WhatsApp (wacli)

Monitora mensagens recebidas via wacli e responde usando o agente.
"""

import subprocess
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from .agent import ConversationalAgent
from .config import AgentConfig

log = logging.getLogger(__name__)


class WhatsAppBridge:
    """
    Bridge entre wacli (WhatsApp CLI) e o agente conversacional.

    Comandos wacli utilizados:
    - wacli messages search --query "..." --limit N
    - wacli send text --to PHONE --message "..."
    - wacli sync --follow (daemon)
    - wacli contacts list
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig.from_env()
        self.agent = ConversationalAgent(self.config)
        self.allowed_contacts: list[str] = []  # JIDs permitidos
        self.auto_reply = True

    def _run_wacli(self, args: list[str]) -> str:
        """Executa comando wacli."""
        cmd = ["wacli"] + args
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                log.error(f"wacli error: {result.stderr}")
                return ""
            return result.stdout
        except FileNotFoundError:
            log.error("wacli não encontrado. Instale via: go install github.com/nicedoc/wacli@latest")
            return ""
        except subprocess.TimeoutExpired:
            log.error("wacli timeout")
            return ""

    def send_message(self, to: str, message: str) -> bool:
        """Envia mensagem via wacli."""
        output = self._run_wacli(["send", "text", "--to", to, "--message", message])
        success = "sent" in output.lower() or output.strip() != ""
        log.info(f"WhatsApp send to={to}: {'ok' if success else 'falha'}")
        return success

    def search_messages(self, query: str, limit: int = 10) -> list[dict]:
        """Busca mensagens."""
        output = self._run_wacli(["messages", "search", "--query", query, "--limit", str(limit), "--json"])
        try:
            return json.loads(output) if output else []
        except json.JSONDecodeError:
            return []

    def list_contacts(self) -> list[dict]:
        """Lista contatos."""
        output = self._run_wacli(["contacts", "list", "--json"])
        try:
            return json.loads(output) if output else []
        except json.JSONDecodeError:
            return []

    def process_incoming(self, message: dict) -> Optional[str]:
        """
        Processa mensagem recebida e gera resposta do agente.

        Args:
            message: dict com 'from', 'text', 'timestamp'

        Returns:
            Resposta do agente ou None se não deve responder
        """
        sender = message.get("from", "")
        text = message.get("text", "").strip()

        if not text:
            return None

        # Verificar se deve responder
        if self.allowed_contacts and sender not in self.allowed_contacts:
            log.debug(f"Contato não autorizado: {sender}")
            return None

        # Ignorar mensagens muito curtas ou comandos
        if len(text) < 3:
            return None

        # Processar com o agente
        log.info(f"WhatsApp incoming: from={sender} text='{text[:50]}...'")
        result = self.agent.chat(text, user=sender)

        response = result["response"]

        # Enviar resposta automaticamente
        if self.auto_reply:
            self.send_message(sender, response)

        return response

    def get_status(self) -> dict:
        """Status da integração."""
        return {
            "wacli_available": self._check_wacli(),
            "auto_reply": self.auto_reply,
            "allowed_contacts": len(self.allowed_contacts),
            "agent": self.config.name,
        }

    def _check_wacli(self) -> bool:
        """Verifica se wacli está disponível."""
        try:
            result = subprocess.run(["wacli", "version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
