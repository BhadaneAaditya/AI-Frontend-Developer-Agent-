"""
LLM Client — unified interface for OpenAI and Anthropic.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from config_loader import config


# ---------------------------------------------------------------------------
# Prompt library
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a Senior Frontend Developer AI Agent specialized in building modern \
web applications.

Your expertise:
• React 18+, Next.js 14 (App Router), TypeScript 5
• TailwindCSS, CSS Modules, styled-components
• Component architecture, design patterns, accessibility (WCAG 2.1 AA)
• Responsive / mobile-first design
• Performance optimisation and SEO best practices

Rules:
1. Analyse the requirements thoroughly before writing code.
2. Decompose the UI into small, reusable, well-typed components.
3. Generate clean, production-grade TypeScript code with JSDoc where helpful.
4. Always use proper TypeScript generics, interfaces, and unions — never `any`.
5. Use TailwindCSS utility classes unless explicitly told otherwise.
6. Output ONLY valid JSON when asked for JSON — no markdown fences, no commentary.
"""

CODE_GENERATION_PROMPT = """\
Task: {task}

Requirements:
- Framework: {framework}
- Styling:   {styling}
- Language:  TypeScript
- Components needed: {components}
- Features:  {features}

Generate a complete project.  Output a **single JSON object** (no markdown):
{{
  "components": [
    {{"name": "ComponentName", "file_path": "components/ComponentName.tsx", "code": "<full code>", "description": "what this does"}}
  ],
  "pages": [
    {{"name": "PageName", "file_path": "app/page.tsx", "code": "<full code>", "description": ""}}
  ],
  "config_files": [
    {{"name": "tailwind.config", "file_path": "tailwind.config.ts", "code": "<config>"}}
  ],
  "explanation": "Short paragraph of what was built"
}}

Rules:
• Every component must have all imports and a default export.
• Pages live under `app/` (Next.js 14 App Router).
• Use TailwindCSS for styling.
• Make everything responsive (mobile-first).
"""

MODIFICATION_PROMPT = """\
Modify the following code.  Instruction: {modification}

File: {file_path}

Current code:
```tsx
{code}
```

Output a single JSON object (no markdown):
{{
  "modified_code": "<complete modified file — keep every import/export>",
  "changes": ["list of changes made"],
  "explanation": "why these changes were made"
}}
"""

BUGFIX_PROMPT = """\
Fix the bug described below.

File: {file_path}
Bug: {bug_description}

Current code:
```tsx
{code}
```

Output a single JSON object (no markdown):
{{
  "modified_code": "<complete fixed code>",
  "root_cause": "what was wrong",
  "fix_description": "how it was fixed",
  "explanation": "summary"
}}
"""


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class LLMClient:
    """Thin wrapper around OpenAI / Anthropic chat completion APIs."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.provider = provider or config.llm_provider
        self.model = model or config.llm_model
        self.api_key = api_key or config.llm_api_key
        self.temperature = config.llm_temperature
        self.max_tokens = config.llm_max_tokens
        self._client: Any = None
        self._init_client()

    # ------------------------------------------------------------------
    def _init_client(self) -> None:
        if self.provider == "openai":
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("Install openai: pip install openai")
        elif self.provider == "anthropic":
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("Install anthropic: pip install anthropic")
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens or self.max_tokens

        if self.provider == "openai":
            return self._call_openai(prompt, system_prompt, temp, tokens)
        return self._call_anthropic(prompt, system_prompt, temp, tokens)

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Call the LLM and parse the result as JSON."""
        raw = self.generate(prompt, system_prompt)
        return self._parse_json(raw)

    # ------------------------------------------------------------------
    # Provider-specific calls
    # ------------------------------------------------------------------
    def _call_openai(
        self, prompt: str, system: Optional[str], temp: float, tokens: int
    ) -> str:
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
        )
        return resp.choices[0].message.content

    def _call_anthropic(
        self, prompt: str, system: Optional[str], temp: float, tokens: int
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": tokens,
            "temperature": temp,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system

        resp = self._client.messages.create(**kwargs)
        return resp.content[0].text

    # ------------------------------------------------------------------
    # JSON extraction
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        """Best-effort extraction of JSON from an LLM response."""
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Strip markdown code fences
        cleaned = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
        cleaned = re.sub(r"```\s*$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Find first { ... } block
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse LLM output as JSON:\n{text[:500]}")
