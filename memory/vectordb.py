"""
Agent Memory — SQLite-backed persistence for tasks, components, and projects.

Uses SQLAlchemy 2.0 style with proper session scoping to avoid
DetachedInstanceError issues.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


# ---------------------------------------------------------------------------
# ORM base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    task_type = Column(String(50), default="frontend")
    framework = Column(String(50), default="nextjs")
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ComponentRecord(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), nullable=False, index=True)
    component_name = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    description = Column(Text, default="")
    code = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ProjectRecord(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(100), unique=True, nullable=False, index=True)
    project_name = Column(String(200), nullable=False)
    task_id = Column(String(100), nullable=True, index=True)
    framework = Column(String(50), default="nextjs")
    structure_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Plain dict helpers (to avoid detached-instance problems)
# ---------------------------------------------------------------------------

def _task_to_dict(t: TaskRecord) -> Dict[str, Any]:
    return {
        "task_id": t.task_id,
        "description": t.description,
        "task_type": t.task_type,
        "framework": t.framework,
        "status": t.status,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


def _component_to_dict(c: ComponentRecord) -> Dict[str, Any]:
    return {
        "component_name": c.component_name,
        "file_path": c.file_path,
        "description": c.description,
        "code": c.code,
        "task_id": c.task_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _project_to_dict(p: ProjectRecord) -> Dict[str, Any]:
    return {
        "project_id": p.project_id,
        "project_name": p.project_name,
        "task_id": p.task_id,
        "framework": p.framework,
        "structure_json": p.structure_json,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# ---------------------------------------------------------------------------
# Main memory class
# ---------------------------------------------------------------------------

class AgentMemory:
    def __init__(self, db_path: str = "./memory/agent_memory.db"):
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self._session_factory = sessionmaker(bind=self.engine)

    @contextmanager
    def _session(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------
    def save_task(
        self,
        task_id: str,
        description: str,
        task_type: str = "frontend",
        framework: str = "nextjs",
        status: str = "pending",
    ) -> Dict[str, Any]:
        with self._session() as s:
            rec = TaskRecord(
                task_id=task_id,
                description=description,
                task_type=task_type,
                framework=framework,
                status=status,
            )
            s.add(rec)
            s.flush()
            return _task_to_dict(rec)

    def update_task_status(self, task_id: str, status: str) -> Optional[Dict[str, Any]]:
        with self._session() as s:
            rec = s.query(TaskRecord).filter_by(task_id=task_id).first()
            if rec:
                rec.status = status
                rec.updated_at = datetime.now(timezone.utc)
                s.flush()
                return _task_to_dict(rec)
        return None

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as s:
            rec = s.query(TaskRecord).filter_by(task_id=task_id).first()
            return _task_to_dict(rec) if rec else None

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        with self._session() as s:
            rows = s.query(TaskRecord).order_by(TaskRecord.created_at.desc()).all()
            return [_task_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Components
    # ------------------------------------------------------------------
    def save_component(
        self,
        task_id: str,
        component_name: str,
        file_path: str,
        description: str = "",
        code: str = "",
    ) -> Dict[str, Any]:
        with self._session() as s:
            rec = ComponentRecord(
                task_id=task_id,
                component_name=component_name,
                file_path=file_path,
                description=description,
                code=code,
            )
            s.add(rec)
            s.flush()
            return _component_to_dict(rec)

    def get_components_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        with self._session() as s:
            rows = (
                s.query(ComponentRecord)
                .filter_by(task_id=task_id)
                .order_by(ComponentRecord.created_at)
                .all()
            )
            return [_component_to_dict(r) for r in rows]

    def search_components(self, query: str) -> List[Dict[str, Any]]:
        with self._session() as s:
            rows = (
                s.query(ComponentRecord)
                .filter(
                    ComponentRecord.component_name.contains(query)
                    | ComponentRecord.description.contains(query)
                )
                .limit(50)
                .all()
            )
            return [_component_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def save_project(
        self,
        project_id: str,
        project_name: str,
        task_id: Optional[str] = None,
        framework: str = "nextjs",
        structure_json: str = "[]",
    ) -> Dict[str, Any]:
        with self._session() as s:
            rec = ProjectRecord(
                project_id=project_id,
                project_name=project_name,
                task_id=task_id,
                framework=framework,
                structure_json=structure_json,
            )
            s.add(rec)
            s.flush()
            return _project_to_dict(rec)

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._session() as s:
            rec = s.query(ProjectRecord).filter_by(project_id=project_id).first()
            return _project_to_dict(rec) if rec else None
