"""
Task Planner — parses free-text task descriptions into structured TaskPlan objects.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class TaskType(Enum):
    FRONTEND = "frontend"
    MODIFICATION = "modification"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"


class Framework(Enum):
    REACT = "react"
    NEXTJS = "nextjs"
    VUE = "vue"
    ANGULAR = "angular"


class Styling(Enum):
    TAILWIND = "tailwindcss"
    STYLED_COMPONENTS = "styled-components"
    CSS_MODULES = "css-modules"
    SCSS = "scss"
    VANILLA = "vanilla-css"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class UIComponent:
    """A single UI element identified in the task."""
    name: str
    type: str
    description: str
    props: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskPlan:
    """Structured representation of a parsed user task."""
    task_id: str
    original_description: str
    task_type: TaskType = TaskType.FRONTEND
    framework: Framework = Framework.NEXTJS
    styling: Styling = Styling.TAILWIND
    page_name: str = ""
    components: List[UIComponent] = field(default_factory=list)
    required_features: List[str] = field(default_factory=list)
    target_file: Optional[str] = None
    modification_description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "original_description": self.original_description,
            "task_type": self.task_type.value,
            "framework": self.framework.value,
            "styling": self.styling.value,
            "page_name": self.page_name,
            "components": [
                {"name": c.name, "type": c.type, "description": c.description}
                for c in self.components
            ],
            "required_features": self.required_features,
            "target_file": self.target_file,
            "modification_description": self.modification_description,
        }


# ---------------------------------------------------------------------------
# Requirement Parser
# ---------------------------------------------------------------------------

class RequirementParser:
    """Rule-based extraction of UI components, framework, and features."""

    FRAMEWORK_KW = {
        "react": Framework.REACT,
        "next": Framework.NEXTJS,
        "nextjs": Framework.NEXTJS,
        "next.js": Framework.NEXTJS,
        "vue": Framework.VUE,
        "angular": Framework.ANGULAR,
    }

    STYLING_KW = {
        "tailwind": Styling.TAILWIND,
        "tailwindcss": Styling.TAILWIND,
        "styled-component": Styling.STYLED_COMPONENTS,
        "styled component": Styling.STYLED_COMPONENTS,
        "css modules": Styling.CSS_MODULES,
        "scss": Styling.SCSS,
        "sass": Styling.SCSS,
        "vanilla css": Styling.VANILLA,
    }

    COMPONENT_KW = {
        "button": "button", "input": "input", "form": "form",
        "card": "card", "modal": "modal", "dialog": "modal",
        "navbar": "navigation", "nav": "navigation",
        "sidebar": "navigation", "header": "header", "footer": "footer",
        "chart": "chart", "graph": "chart",
        "table": "table", "dropdown": "dropdown", "select": "select",
        "checkbox": "checkbox", "radio": "radio", "textarea": "textarea",
        "avatar": "avatar", "badge": "badge", "alert": "alert",
        "loader": "loader", "spinner": "loader",
        "menu": "menu", "tabs": "tabs", "tab": "tabs",
        "accordion": "accordion", "carousel": "carousel",
        "tooltip": "tooltip", "popover": "popover",
        "search": "search", "pagination": "pagination",
        "breadcrumb": "breadcrumb", "stepper": "stepper",
        "toast": "toast", "notification": "notification",
        "progress": "progress", "skeleton": "skeleton",
        "toggle": "toggle", "switch": "toggle",
    }

    FEATURE_KW = {
        "responsive": "responsive design",
        "mobile": "mobile responsiveness",
        "accessible": "accessibility (WCAG 2.1 AA)",
        "dark mode": "dark mode support",
        "theme": "theming support",
        "animate": "animations & transitions",
        "animation": "animations & transitions",
        "validate": "form validation",
        "validation": "form validation",
        "auth": "authentication",
        "api": "API integration",
        "state": "state management",
        "hook": "custom hooks",
        "context": "React context",
        "router": "client-side routing",
        "seo": "SEO optimisation",
        "i18n": "internationalisation",
        "pagination": "pagination",
        "infinite scroll": "infinite scroll",
        "drag": "drag & drop",
        "real-time": "real-time updates",
        "websocket": "WebSocket integration",
    }

    KNOWN_PAGES = [
        "login", "signup", "register", "dashboard", "home", "landing",
        "profile", "settings", "admin", "chat", "analytics", "ecommerce",
        "checkout", "pricing", "about", "contact", "blog", "portfolio",
        "calendar", "kanban", "inbox", "notifications",
    ]

    # ------------------------------------------------------------------
    def parse(self, task_description: str, task_type: str = "frontend") -> TaskPlan:
        task_id = uuid.uuid4().hex[:8]
        lower = task_description.lower()

        plan = TaskPlan(
            task_id=task_id,
            original_description=task_description,
            task_type=self._detect_task_type(lower, task_type),
            framework=self._detect_framework(lower),
            styling=self._detect_styling(lower),
            page_name=self._extract_page_name(task_description),
            components=self._extract_components(task_description),
            required_features=self._extract_features(lower),
        )

        if plan.task_type in (TaskType.MODIFICATION, TaskType.BUGFIX, TaskType.REFACTOR):
            plan.modification_description = task_description

        return plan

    # ------------------------------------------------------------------
    def _detect_task_type(self, lower: str, explicit: str) -> TaskType:
        try:
            return TaskType(explicit)
        except ValueError:
            pass

        if any(kw in lower for kw in ("bug", "fix", "error", "broken", "crash")):
            return TaskType.BUGFIX
        if any(kw in lower for kw in ("refactor", "restructure", "clean up")):
            return TaskType.REFACTOR
        if any(kw in lower for kw in ("modify", "change", "update", "make", "add to")):
            return TaskType.MODIFICATION
        return TaskType.FRONTEND

    def _detect_framework(self, lower: str) -> Framework:
        for kw, fw in self.FRAMEWORK_KW.items():
            if kw in lower:
                return fw
        return Framework.NEXTJS

    def _detect_styling(self, lower: str) -> Styling:
        for kw, st in self.STYLING_KW.items():
            if kw in lower:
                return st
        return Styling.TAILWIND

    def _extract_page_name(self, description: str) -> str:
        lower = description.lower()
        for name in self.KNOWN_PAGES:
            if name in lower:
                return name

        patterns = [
            r"(?:create|build|make|design)\s+(?:a\s+)?(\w+)\s+(?:page|ui|screen|view|dashboard|form|modal|panel)",
            r"(\w+)\s+(?:page|dashboard|panel|screen)\b",
        ]
        for p in patterns:
            m = re.search(p, lower)
            if m:
                return m.group(1)

        return "page"

    def _extract_components(self, description: str) -> List[UIComponent]:
        lower = description.lower()
        seen: set[str] = set()
        components: List[UIComponent] = []
        for kw, ctype in self.COMPONENT_KW.items():
            if kw in lower and ctype not in seen:
                seen.add(ctype)
                name = ctype.replace(" ", "").title()
                components.append(
                    UIComponent(
                        name=f"{name}Component",
                        type=ctype,
                        description=f"{ctype} component for the UI",
                    )
                )
        return components

    def _extract_features(self, lower: str) -> List[str]:
        features: List[str] = []
        for kw, feat in self.FEATURE_KW.items():
            if kw in lower and feat not in features:
                features.append(feat)
        return features


# ---------------------------------------------------------------------------
# Task Planner (public facade)
# ---------------------------------------------------------------------------

class TaskPlanner:
    def __init__(self) -> None:
        self.parser = RequirementParser()

    def create_plan(self, task_description: str, task_type: str = "frontend") -> TaskPlan:
        return self.parser.parse(task_description, task_type)

    def refine_plan(self, plan: TaskPlan, additional_info: str) -> TaskPlan:
        extra = self.parser.parse(additional_info, plan.task_type.value)
        existing_names = {c.name for c in plan.components}
        for c in extra.components:
            if c.name not in existing_names:
                plan.components.append(c)
        for f in extra.required_features:
            if f not in plan.required_features:
                plan.required_features.append(f)
        return plan

    @staticmethod
    def get_component_list(plan: TaskPlan) -> str:
        if not plan.components:
            return "Main page component"
        return ", ".join(c.name for c in plan.components)
