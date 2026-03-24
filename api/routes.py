"""
FastAPI routes for the Frontend Developer Agent.

All endpoints live under the /api/v1 prefix (set in main.py).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent.planner import TaskPlanner
from agent.generator import CodeGenerator
from agent.editor import CodeEditor
from agent.llm_client import LLMClient
from memory.vectordb import AgentMemory
from executor.file_writer import FileWriter
from executor.code_runner import CodeRunner
from config_loader import config

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Shared service instances (created once on module import)
# ---------------------------------------------------------------------------

memory = AgentMemory(config.memory_db_path)
planner = TaskPlanner()
llm_client = LLMClient()
generator = CodeGenerator(llm_client)
editor = CodeEditor(llm_client)
file_writer = FileWriter(config.output_dir)
code_runner = CodeRunner()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class TaskRequest(BaseModel):
    task: str = Field(..., description="Natural-language task description")
    task_type: str = Field("frontend", description="frontend | modification | bugfix | refactor")
    framework: str = Field("nextjs", description="Target framework")
    styling: str = Field("tailwindcss", description="Styling approach")


class GenerateRequest(BaseModel):
    task: str
    task_type: str = "frontend"
    framework: str = "nextjs"
    styling: str = "tailwindcss"
    context: Optional[str] = Field(None, description="Additional context for generation")


class ModifyRequest(BaseModel):
    file_path: str
    modification: str
    current_code: str


class BugFixRequest(BaseModel):
    file_path: str
    bug_description: str
    current_code: str


class RefactorRequest(BaseModel):
    file_path: str
    refactor_type: str
    current_code: str


class AddComponentRequest(BaseModel):
    project_path: str
    component_name: str
    component_type: str = "component"


class RunCommandRequest(BaseModel):
    project_path: str
    command: str = Field("npm install", description="Shell command to execute")


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_provider": config.llm_provider,
        "llm_model": config.llm_model,
        "output_dir": config.output_dir,
    }


# ---------------------------------------------------------------------------
# 1.  POST /task  — parse a task into a plan (no generation)
# ---------------------------------------------------------------------------

@router.post("/task")
async def create_task(req: TaskRequest):
    try:
        plan = planner.create_plan(req.task, req.task_type)

        memory.save_task(
            task_id=plan.task_id,
            description=req.task,
            task_type=req.task_type,
            framework=req.framework,
            status="planned",
        )

        return {
            "status": "success",
            "task_id": plan.task_id,
            "plan": plan.to_dict(),
        }
    except Exception as exc:
        logger.exception("POST /task failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 2.  POST /generate  — plan + generate + write files
# ---------------------------------------------------------------------------

@router.post("/generate")
async def generate_code(req: GenerateRequest):
    try:
        plan = planner.create_plan(req.task, req.task_type)

        memory.save_task(
            task_id=plan.task_id,
            description=req.task,
            task_type=req.task_type,
            framework=req.framework,
            status="generating",
        )

        if req.context:
            project = generator.generate_with_context(plan, req.context)
        else:
            project = generator.generate(plan)

        result = file_writer.write_project(project)

        # Persist components + pages
        for comp in project.components + project.pages:
            memory.save_component(
                task_id=plan.task_id,
                component_name=comp.name,
                file_path=comp.file_path,
                description=comp.description,
                code=comp.code,
            )

        memory.update_task_status(plan.task_id, "completed")

        return {
            "status": "completed",
            "task_id": plan.task_id,
            "plan": plan.to_dict(),
            "files_created": result["files_created"],
            "project_path": result["project_path"],
            "structure": result["structure"],
            "explanation": project.explanation,
        }
    except Exception as exc:
        logger.exception("POST /generate failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 3.  POST /modify
# ---------------------------------------------------------------------------

@router.post("/modify")
async def modify_code(req: ModifyRequest):
    try:
        result = editor.modify(req.file_path, req.modification, req.current_code)
        if result.success:
            file_writer.write_single_file(req.file_path, result.modified_code)
        return result.to_dict()
    except Exception as exc:
        logger.exception("POST /modify failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 4.  POST /bugfix
# ---------------------------------------------------------------------------

@router.post("/bugfix")
async def fix_bug(req: BugFixRequest):
    try:
        result = editor.fix_bug(req.file_path, req.bug_description, req.current_code)
        if result.success:
            file_writer.write_single_file(req.file_path, result.modified_code)
        return result.to_dict()
    except Exception as exc:
        logger.exception("POST /bugfix failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 5.  POST /refactor
# ---------------------------------------------------------------------------

@router.post("/refactor")
async def refactor_code(req: RefactorRequest):
    try:
        result = editor.refactor(req.file_path, req.refactor_type, req.current_code)
        if result.success:
            file_writer.write_single_file(req.file_path, result.modified_code)
        return result.to_dict()
    except Exception as exc:
        logger.exception("POST /refactor failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 6.  POST /add-component
# ---------------------------------------------------------------------------

@router.post("/add-component")
async def add_component(req: AddComponentRequest):
    try:
        code = editor.add_component(
            project_path=req.project_path,
            component_name=req.component_name,
            component_type=req.component_type,
        )
        file_path = f"{req.project_path}/components/{req.component_name}.tsx"
        file_writer.write_single_file(file_path, code)
        return {"status": "success", "file_path": file_path, "code": code}
    except Exception as exc:
        logger.exception("POST /add-component failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 7.  POST /run  — execute a command inside a project directory
# ---------------------------------------------------------------------------

@router.post("/run")
async def run_command(req: RunCommandRequest):
    try:
        result = await code_runner.run_async(req.command, cwd=req.project_path)
        return result.to_dict()
    except Exception as exc:
        logger.exception("POST /run failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 8.  GET /tasks  — list all tasks
# ---------------------------------------------------------------------------

@router.get("/tasks")
async def get_tasks():
    try:
        tasks = memory.get_all_tasks()
        return {"tasks": tasks}
    except Exception as exc:
        logger.exception("GET /tasks failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 9.  GET /task/{task_id}  — single task with components
# ---------------------------------------------------------------------------

@router.get("/task/{task_id}")
async def get_task(task_id: str):
    try:
        task = memory.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        components = memory.get_components_by_task(task_id)
        return {"task": task, "components": components}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("GET /task/%s failed", task_id)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 10.  GET /components/search?q=<query>
# ---------------------------------------------------------------------------

@router.get("/components/search")
async def search_components(q: str = ""):
    try:
        results = memory.search_components(q) if q else []
        return {"results": results}
    except Exception as exc:
        logger.exception("GET /components/search failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# 11.  GET /projects  — list generated project directories
# ---------------------------------------------------------------------------

@router.get("/projects")
async def list_projects():
    try:
        output_dir = Path(config.output_dir)
        if not output_dir.exists():
            return {"projects": []}

        projects = [
            {"name": d.name, "path": str(d)}
            for d in sorted(output_dir.iterdir())
            if d.is_dir()
        ]
        return {"projects": projects}
    except Exception as exc:
        logger.exception("GET /projects failed")
        raise HTTPException(status_code=500, detail=str(exc))
