"""Prompt-injection screening for user requests and retrieved passages."""

from __future__ import annotations

import re
from typing import Any

from rag.retrieve import Passage

_INJECTION_PATTERNS = [
    ("ignore_previous_instructions", re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I)),
    ("reveal_system_prompt", re.compile(r"(?:reveal|disclose|print|show)\s+(the\s+)?(system|hidden|developer)\s+prompt", re.I)),
    ("api_key_exfiltration", re.compile(r"send\s+(any\s+)?api\s+key|exfiltrat", re.I)),
    ("system_override", re.compile(r"override\s+(the\s+)?(system|developer)\s+(prompt|instructions?)", re.I)),
    ("developer_instruction_override", re.compile(r"ignore\s+(all\s+)?developer\s+(instructions?|messages?)", re.I)),
]


def injection_rules(text: str) -> list[str]:
    return [name for name, pattern in _INJECTION_PATTERNS if pattern.search(text)]


def contains_injection(text: str) -> bool:
    return bool(injection_rules(text))


def screen_passages(passages: list[Passage]) -> tuple[list[Passage], list[dict[str, Any]]]:
    safe: list[Passage] = []
    actions: list[dict[str, Any]] = []
    for passage in passages:
        rules = injection_rules(passage.text)
        if rules:
            actions.extend({
                "rule_name": rule,
                "chunk_id": passage.chunk_id,
                "doc_id": passage.doc_id,
                "action_taken": "removed",
            } for rule in rules)
        else:
            safe.append(passage)
    return safe, actions


def screen_query(query: str) -> tuple[str, list[dict[str, Any]]]:
    rules = injection_rules(query)
    if rules:
        return "", [{
            "rule_name": rule,
            "chunk_id": None,
            "doc_id": None,
            "action_taken": "blocked_user_query",
        } for rule in rules]
    return query, []
