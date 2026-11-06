import logging
from typing import List, Dict, Tuple, Any

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """
    Estimates token count using character heuristic: max(1, int(chars / 3.5)).
    Matches Groq / Llama / Qwen / GPT tokenizer average character-to-token ratio.
    """
    if not text:
        return 0
    return max(1, int(len(text) / 3.5))

def truncate_text_to_token_budget(text: str, max_tokens: int) -> Tuple[str, bool]:
    """
    Truncates text to stay within max_tokens budget (chars = max_tokens * 3.5).
    Appends a clear truncation note if truncation was required.
    """
    if not text:
        return "", False
    max_chars = int(max_tokens * 3.5)
    if len(text) <= max_chars:
        return text, False
    truncated = text[:max_chars].rstrip() + "\n\n[... Source context truncated to conform with model context token budget ...]"
    return truncated, True

class TokenBudgetManager:
    """
    Enforces per-model context cap and standard budget allocation:
    - Total working cap: 8,192 tokens (safe operational ceiling)
    - System prompt: 10% (819 tokens)
    - Grounded sources: 40% (3,276 tokens)
    - Conversation history: 20% (1,638 tokens)
    - User message: 15% (1,228 tokens)
    - LLM generation output: 15% (1,228 tokens)
    
    Guarantees:
    - Never trims user's question.
    - Trims oldest conversation history turns first.
    - Truncates source text when exceeding 40% budget and flags for response notification.
    """
    DEFAULT_CAP = 8192

    @classmethod
    def get_context_cap(cls, model_name: str) -> int:
        return cls.DEFAULT_CAP

    @classmethod
    def allocate_budgets(cls, model_name: str) -> Dict[str, int]:
        cap = cls.get_context_cap(model_name)
        return {
            "total": cap,
            "system": int(cap * 0.10),
            "sources": int(cap * 0.40),
            "history": int(cap * 0.20),
            "user": int(cap * 0.15),
            "output": int(cap * 0.15)
        }

    @classmethod
    def prepare_chat_payload(
        cls,
        model_name: str,
        system_prompt: str,
        sources_text: str,
        history: List[Dict[str, str]],
        user_message: str
    ) -> Dict[str, Any]:
        budgets = cls.allocate_budgets(model_name)

        # 1. System prompt (10% budget)
        trimmed_system, _ = truncate_text_to_token_budget(system_prompt, budgets["system"])

        # 2. User message (Never trimmed)
        user_tokens = estimate_tokens(user_message)

        # 3. Sources (40% budget)
        trimmed_sources, sources_truncated = truncate_text_to_token_budget(sources_text, budgets["sources"])

        # 4. History (20% budget - oldest first pruned)
        trimmed_history = []
        accumulated_history_tokens = 0
        for msg in reversed(history):
            content = msg.get("content", "")
            msg_tokens = estimate_tokens(content)
            if accumulated_history_tokens + msg_tokens <= budgets["history"]:
                trimmed_history.insert(0, msg)
                accumulated_history_tokens += msg_tokens
            else:
                break

        estimated_input_tokens = (
            estimate_tokens(trimmed_system)
            + estimate_tokens(trimmed_sources)
            + accumulated_history_tokens
            + user_tokens
        )

        return {
            "system_prompt": trimmed_system,
            "sources_text": trimmed_sources,
            "sources_truncated": sources_truncated,
            "history": trimmed_history,
            "user_message": user_message,
            "budgets": budgets,
            "estimated_input_tokens": estimated_input_tokens
        }

