"""
Frontend Developer Agent — high-level orchestrator.

Usage:
    from frontend_dev_agent import create_agent
    agent = create_agent(api_key="sk-...")
    result = agent.build("Create a login page with email and password fields")
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from agent.planner import TaskPlanner, TaskPlan
from agent.generator import CodeGenerator
from agent.editor import CodeEditor
from agent.llm_client import LLMClient
from memory.vectordb import AgentMemory
from executor.file_writer import FileWriter
from executor.code_runner import CodeRunner
from config_loader import config

logger = logging.getLogger(__name__)


class FrontendDevAgent:
    """
    End-to-end agent: task → plan → generate → write → remember → explain.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.memory = AgentMemory(config.memory_db_path)
        self.planner = TaskPlanner()
        self.llm = LLMClient(api_key=api_key) if api_key else LLMClient()
        self.generator = CodeGenerator(self.llm)
        self.editor = CodeEditor(self.llm)
        self.file_writer = FileWriter(config.output_dir)
        self.code_runner = CodeRunner()

    # ------------------------------------------------------------------
    # 1. BUILD — generate a full project from a natural-language task
    # ------------------------------------------------------------------
    def build(self, task_description: str, task_type: str = "frontend") -> Dict[str, Any]:
        # Plan
        plan = self.planner.create_plan(task_description, task_type)
        logger.info("[%s] Plan created → page=%s, components=%d",
                     plan.task_id, plan.page_name, len(plan.components))

        # Persist task
        self.memory.save_task(
            task_id=plan.task_id,
            description=task_description,
            task_type=task_type,
            framework=plan.framework.value,
            status="generating",
        )

        # Generate
        project = self.generator.generate(plan)

        # Write to disk
        result = self.file_writer.write_project(project)

        # Persist all generated components/pages
        for comp in project.components + project.pages:
            self.memory.save_component(
                task_id=plan.task_id,
                component_name=comp.name,
                file_path=comp.file_path,
                description=comp.description,
                code=comp.code,
            )

        # Persist project record
        self.memory.save_project(
            project_id=plan.task_id,
            project_name=project.project_name,
            task_id=plan.task_id,
            framework=plan.framework.value,
            structure_json=json.dumps(project.structure),
        )

        self.memory.update_task_status(plan.task_id, "completed")

        return {
            "status": "completed",
            "task_id": plan.task_id,
            "project_path": result["project_path"],
            "files_created": result["files_created"],
            "structure": result["structure"],
            "explanation": project.explanation,
            "plan": plan.to_dict(),
        }

    # ------------------------------------------------------------------
    # 2. MODIFY — update an existing file
    # ------------------------------------------------------------------
    def modify(
        self,
        file_path: str,
        modification: str,
        current_code: str,
    ) -> Dict[str, Any]:
        result = self.editor.modify(file_path, modification, current_code)
        if result.success:
            self.file_writer.write_single_file(file_path, result.modified_code)
        return result.to_dict()

    # ------------------------------------------------------------------
    # 3. BUG FIX
    # ------------------------------------------------------------------
    def fix_bug(
        self,
        file_path: str,
        bug_description: str,
        current_code: str,
    ) -> Dict[str, Any]:
        result = self.editor.fix_bug(file_path, bug_description, current_code)
        if result.success:
            self.file_writer.write_single_file(file_path, result.modified_code)
        return result.to_dict()

    # ------------------------------------------------------------------
    # 4. REFACTOR
    # ------------------------------------------------------------------
    def refactor(
        self,
        file_path: str,
        refactor_type: str,
        current_code: str,
    ) -> Dict[str, Any]:
        result = self.editor.refactor(file_path, refactor_type, current_code)
        if result.success:
            self.file_writer.write_single_file(file_path, result.modified_code)
        return result.to_dict()

    # ------------------------------------------------------------------
    # 5. ADD COMPONENT to an existing project
    # ------------------------------------------------------------------
    def add_component(
        self,
        project_path: str,
        component_name: str,
    ) -> Dict[str, Any]:
        code = self.editor.add_component(project_path, component_name)
        file_path = f"{project_path}/components/{component_name}.tsx"
        self.file_writer.write_single_file(file_path, code)
        return {"file_path": file_path, "code": code}

    # ------------------------------------------------------------------
    # Memory queries
    # ------------------------------------------------------------------
    def get_task_history(self) -> List[Dict[str, Any]]:
        return self.memory.get_all_tasks()

    def get_task_detail(self, task_id: str) -> Optional[Dict[str, Any]]:
        task = self.memory.get_task(task_id)
        if not task:
            return None
        components = self.memory.get_components_by_task(task_id)
        return {"task": task, "components": components}

    def search_components(self, query: str) -> List[Dict[str, Any]]:
        return self.memory.search_components(query)


# ---------------------------------------------------------------------------
# Factory function (public API)
# ---------------------------------------------------------------------------

def create_agent(api_key: Optional[str] = None) -> FrontendDevAgent:
    """Create and return a ready-to-use FrontendDevAgent instance."""
    return FrontendDevAgent(api_key=api_key)
