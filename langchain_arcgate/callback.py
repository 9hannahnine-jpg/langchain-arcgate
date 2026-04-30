"""
Arc Gate callback handler for LangChain.
Screens every prompt for injection attacks before it reaches your LLM.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage


class ArcGateCallback(BaseCallbackHandler):
    """
    LangChain callback that screens prompts through Arc Gate before
    they reach your LLM. Blocked prompts raise a ValueError.

    Args:
        api_key: Your Arc Gate API key. Use "demo" for evaluation.
        base_url: Arc Gate endpoint. Defaults to the hosted instance.
        raise_on_block: If True (default), raise ValueError on blocked prompts.
                        If False, print a warning and allow the prompt through.
        timeout: Request timeout in seconds. Default 10.

    Example:
        from langchain_arcgate import ArcGateCallback
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(callbacks=[ArcGateCallback(api_key="demo")])
        response = llm.invoke("Hello!")
    """

    def __init__(
        self,
        api_key: str = "demo",
        base_url: str = "https://web-production-6e47f.up.railway.app",
        raise_on_block: bool = True,
        timeout: float = 10.0,
    ):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.raise_on_block = raise_on_block
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def _screen(self, prompt: str) -> dict:
        """Send prompt to Arc Gate for screening. Returns arc_sentry dict."""
        try:
            r = self._client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "screen-only",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1,
                    "stream": False,
                },
            )
            data = r.json()
            return data.get("arc_sentry", {})
        except Exception as e:
            # Never block legitimate traffic due to network issues
            print(f"[ArcGate] Warning: screening failed ({e}), allowing prompt through")
            return {}

    def _handle_result(self, arc: dict, prompt: str) -> None:
        """Handle the screening result."""
        if arc.get("blocked"):
            layer = arc.get("layer", "unknown")
            reason = arc.get("reason", "injection detected")
            msg = f"[Arc Gate] Prompt blocked — {reason} (layer: {layer})"
            if self.raise_on_block:
                raise ValueError(msg)
            else:
                print(f"WARNING: {msg}")

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Screen chat model prompts before they reach the LLM."""
        for message_list in messages:
            for message in message_list:
                content = message.content if hasattr(message, "content") else str(message)
                if isinstance(content, str) and content.strip():
                    arc = self._screen(content)
                    self._handle_result(arc, content)

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Screen non-chat LLM prompts before they reach the LLM."""
        for prompt in prompts:
            if prompt.strip():
                arc = self._screen(prompt)
                self._handle_result(arc, prompt)

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass
