"""Prompt-injection screening for user requests and retrieved passages."""

from __future__ import annotations

import re

from rag.retrieve import Passage

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"(?:reveal|disclose|print|show)\s+(the\s+)?(system|hidden)\s+prompt", re.I),
    re.compile(r"send\s+(any\s+)?api\s+key|exfiltrat", re.I),
    re.compile(r"override\s+(the\s+)?system", re.I),
]


def contains_injection(text: str) -> bool:
    return any(pattern.search(text) for pattern in _INJECTION_PATTERNS)


def screen_passages(passages: list[Passage]) -> tuple[list[Passage], list[str]]:
    safe: list[Passage] = []
    actions: list[str] = []
    for passage in passages:
        if contains_injection(passage.text):
            actions.append(f"injection_blocked:{passage.doc_id}:{passage.chunk_id}")
        else:
            safe.append(passage)
    return safe, actions


def screen_query(query: str) -> tuple[bool, list[str]]:
    if contains_injection(query):
        return True, ["user_instruction_override_blocked"]
    return False, []
