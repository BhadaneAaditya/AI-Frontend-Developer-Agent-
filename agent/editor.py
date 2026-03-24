"""
Code Editor — modify, fix, refactor, and extend existing code via the LLM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent.llm_client import (
    LLMClient,
    SYSTEM_PROMPT,
    MODIFICATION_PROMPT,
    BUGFIX_PROMPT,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

class ModificationResult:
    """Outcome of a code-editing operation."""

    def __init__(
        self,
        modified_code: str,
        explanation: str,
        file_path: str,
        success: bool = True,
        changes: Optional[List[str]] = None,
    ):
        self.modified_code = modified_code
        self.explanation = explanation
        self.file_path = file_path
        self.success = success
        self.changes = changes or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modified_code": self.modified_code,
            "explanation": self.explanation,
            "file_path": self.file_path,
            "success": self.success,
            "changes": self.changes,
        }


# ---------------------------------------------------------------------------
# Editor
# ---------------------------------------------------------------------------

class CodeEditor:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    # ------------------------------------------------------------------
    # 1. Modify
    # ------------------------------------------------------------------
    def modify(
        self,
        file_path: str,
        modification: str,
        current_code: str,
    ) -> ModificationResult:
        prompt = MODIFICATION_PROMPT.format(
            modification=modification,
            file_path=file_path,
            code=current_code,
        )
        return self._execute(prompt, file_path, current_code, "modification")

    # ------------------------------------------------------------------
    # 2. Bug fix
    # ------------------------------------------------------------------
    def fix_bug(
        self,
        file_path: str,
        bug_description: str,
        current_code: str,
    ) -> ModificationResult:
        prompt = BUGFIX_PROMPT.format(
            bug_description=bug_description,
            file_path=file_path,
            code=current_code,
        )
        return self._execute(prompt, file_path, current_code, "bugfix")

    # ------------------------------------------------------------------
    # 3. Refactor
    # ------------------------------------------------------------------
    def refactor(
        self,
        file_path: str,
        refactor_type: str,
        current_code: str,
    ) -> ModificationResult:
        prompt = f"""\
Refactor the code below.  Goal: {refactor_type}

File: {file_path}

Current code:
```tsx
{current_code}
```

Output a single JSON object (no markdown):
{{
  "modified_code": "<complete refactored code>",
  "changes": ["list of refactoring changes"],
  "explanation": "summary"
}}
"""
        return self._execute(prompt, file_path, current_code, "refactor")

    # ------------------------------------------------------------------
    # 4. Add component
    # ------------------------------------------------------------------
    def add_component(
        self,
        project_path: str,
        component_name: str,
        component_type: str = "component",
    ) -> str:
        prompt = f"""\
Generate a new React {component_type} called **{component_name}**.

Requirements:
- Framework: Next.js 14 (App Router)
- Styling: TailwindCSS
- Language: TypeScript
- Must include all imports and a default export
- Must be production-ready with good accessibility

Output a single JSON object (no markdown):
{{
  "code": "<complete component code>"
}}
"""
        try:
            result = self.llm.generate_json(prompt, SYSTEM_PROMPT)
            return result.get("code", "")
        except Exception as exc:
            logger.error("Failed to generate component %s: %s", component_name, exc)
            return f"// Error generating component: {exc}"

    # ------------------------------------------------------------------
    # 5. Update styling
    # ------------------------------------------------------------------
    def update_styling(
        self,
        file_path: str,
        new_styles: str,
        current_code: str,
    ) -> ModificationResult:
        prompt = f"""\
Update the styling in the code below.

File: {file_path}
Style changes requested: {new_styles}

Current code:
```tsx
{current_code}
```

Output a single JSON object (no markdown):
{{
  "modified_code": "<complete updated code>",
  "changes": ["list of style changes"],
  "explanation": "summary"
}}
"""
        return self._execute(prompt, file_path, current_code, "styling")

    # ------------------------------------------------------------------
    # 6. Make responsive
    # ------------------------------------------------------------------
    def make_responsive(
        self,
        file_path: str,
        current_code: str,
    ) -> ModificationResult:
        prompt = f"""\
Make this code fully responsive (mobile-first design).

File: {file_path}

Current code:
```tsx
{current_code}
```

Add responsive TailwindCSS breakpoint classes (sm:, md:, lg:, xl:).
Output a single JSON object (no markdown):
{{
  "modified_code": "<complete responsive code>",
  "changes": ["list of responsive changes"],
  "explanation": "summary"
}}
"""
        return self._execute(prompt, file_path, current_code, "responsive")

    # ------------------------------------------------------------------
    # Shared LLM call
    # ------------------------------------------------------------------
    def _execute(
        self,
        prompt: str,
        file_path: str,
        fallback_code: str,
        operation: str,
    ) -> ModificationResult:
        try:
            data = self.llm.generate_json(prompt, SYSTEM_PROMPT)
            return ModificationResult(
                modified_code=data.get("modified_code", fallback_code),
                explanation=data.get("explanation", f"{operation} applied"),
                file_path=file_path,
                success=True,
                changes=data.get("changes", []),
            )
        except Exception as exc:
            logger.error("Code %s failed for %s: %s", operation, file_path, exc)
            return ModificationResult(
                modified_code=fallback_code,
                explanation=f"Error during {operation}: {exc}",
                file_path=file_path,
                success=False,
            )
