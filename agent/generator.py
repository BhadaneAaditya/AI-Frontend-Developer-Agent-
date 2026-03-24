"""
Code Generator — turns a TaskPlan into a GeneratedProject using the LLM.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from agent.planner import TaskPlan, TaskType
from agent.llm_client import LLMClient, SYSTEM_PROMPT, CODE_GENERATION_PROMPT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

class ComponentCode:
    """A single generated file (component, page, or config)."""

    def __init__(
        self,
        name: str,
        file_path: str,
        code: str,
        description: str = "",
        component_type: str = "component",
    ):
        self.name = name
        self.file_path = file_path
        self.code = code
        self.description = description
        self.component_type = component_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "file_path": self.file_path,
            "code": self.code,
            "description": self.description,
            "component_type": self.component_type,
        }


class GeneratedProject:
    """Collection of all files produced for a single task."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.components: List[ComponentCode] = []
        self.pages: List[ComponentCode] = []
        self.config_files: List[ComponentCode] = []
        self.structure: List[str] = []
        self.explanation: str = ""

    def add_component(self, comp: ComponentCode) -> None:
        self.components.append(comp)
        self.structure.append(comp.file_path)

    def add_page(self, page: ComponentCode) -> None:
        self.pages.append(page)
        self.structure.append(page.file_path)

    def add_config(self, cfg: ComponentCode) -> None:
        self.config_files.append(cfg)
        self.structure.append(cfg.file_path)

    @property
    def all_files(self) -> List[ComponentCode]:
        return self.components + self.pages + self.config_files

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_name": self.project_name,
            "components": [c.to_dict() for c in self.components],
            "pages": [p.to_dict() for p in self.pages],
            "config_files": [c.to_dict() for c in self.config_files],
            "structure": self.structure,
            "explanation": self.explanation,
        }


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class CodeGenerator:
    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm = llm_client or LLMClient()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate(self, plan: TaskPlan) -> GeneratedProject:
        if plan.task_type in (TaskType.MODIFICATION, TaskType.BUGFIX):
            raise ValueError("Use CodeEditor for modifications / bug fixes")

        project = self._new_project(plan)
        prompt = self._build_prompt(plan)

        try:
            result = self.llm.generate_json(prompt, SYSTEM_PROMPT)
            self._hydrate_project(result, project)
            logger.info("LLM code generation succeeded for task %s", plan.task_id)
        except Exception:
            logger.warning(
                "LLM generation failed for task %s — using fallback",
                plan.task_id,
                exc_info=True,
            )
            project = self._fallback(plan)

        return project

    def generate_with_context(self, plan: TaskPlan, context: str) -> GeneratedProject:
        project = self._new_project(plan)
        prompt = self._build_prompt(plan) + f"\n\nAdditional context:\n{context}"

        try:
            result = self.llm.generate_json(prompt, SYSTEM_PROMPT)
            self._hydrate_project(result, project)
        except Exception:
            logger.warning("LLM generation with context failed", exc_info=True)
            project = self._fallback(plan)

        return project

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    @staticmethod
    def _new_project(plan: TaskPlan) -> GeneratedProject:
        name = f"{plan.page_name}-project" if plan.page_name else "frontend-project"
        return GeneratedProject(name)

    def _build_prompt(self, plan: TaskPlan) -> str:
        comps = ", ".join(c.name for c in plan.components) or "Main page component"
        feats = ", ".join(plan.required_features) or "basic UI"

        return CODE_GENERATION_PROMPT.format(
            task=plan.original_description,
            framework=plan.framework.value,
            styling=plan.styling.value,
            components=comps,
            features=feats,
        )

    @staticmethod
    def _hydrate_project(data: Dict[str, Any], project: GeneratedProject) -> None:
        """Populate project from parsed LLM JSON."""
        for item in data.get("components", []):
            project.add_component(ComponentCode(
                name=item.get("name", "Component"),
                file_path=item.get("file_path", "components/Component.tsx"),
                code=item.get("code", ""),
                description=item.get("description", ""),
                component_type="component",
            ))

        for item in data.get("pages", []):
            project.add_page(ComponentCode(
                name=item.get("name", "Page"),
                file_path=item.get("file_path", "app/page.tsx"),
                code=item.get("code", ""),
                description=item.get("description", ""),
                component_type="page",
            ))

        for item in data.get("config_files", []):
            project.add_config(ComponentCode(
                name=item.get("name", "Config"),
                file_path=item.get("file_path", "config.ts"),
                code=item.get("code", ""),
                description=item.get("description", ""),
                component_type="config",
            ))

        project.explanation = data.get("explanation", "")

    # ------------------------------------------------------------------
    # Fallback template (no LLM required)
    # ------------------------------------------------------------------
    def _fallback(self, plan: TaskPlan) -> GeneratedProject:
        project = self._new_project(plan)
        title = plan.page_name.replace("-", " ").title()

        page_code = f'''\
"use client";

import React from "react";

export default function {title.replace(" ", "")}Page() {{
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-6">
      <div className="max-w-lg w-full bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-8 text-center">
        <h1 className="text-3xl font-bold text-white mb-4">
          {title}
        </h1>
        <p className="text-slate-300 leading-relaxed">
          {plan.original_description}
        </p>
      </div>
    </main>
  );
}}
'''
        project.add_page(ComponentCode(
            name=f"{title.replace(' ', '')}Page",
            file_path="app/page.tsx",
            code=page_code,
            description=f"{title} page (fallback template)",
            component_type="page",
        ))
        project.explanation = (
            f"Generated a {title} page with TailwindCSS styling (fallback mode — "
            f"LLM was unavailable)."
        )
        return project
