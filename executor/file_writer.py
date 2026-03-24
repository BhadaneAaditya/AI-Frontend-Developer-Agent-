"""
File Writer — writes GeneratedProject contents to disk with proper Next.js
scaffolding (App Router, Tailwind, TypeScript configs).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from agent.generator import GeneratedProject, ComponentCode

logger = logging.getLogger(__name__)


class FileWriter:
    def __init__(self, output_dir: str = "./generated_projects"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_project(self, project: GeneratedProject) -> Dict[str, Any]:
        """Write all project files to disk and return a summary dict."""
        project_path = self.output_dir / project.project_name
        project_path.mkdir(parents=True, exist_ok=True)

        files_written: List[str] = []

        # 1. Scaffold config files first
        self._write_scaffold(project_path, project)

        # 2. User-generated config files
        for cfg in project.config_files:
            fp = project_path / cfg.file_path
            self._safe_write(fp, cfg.code)
            files_written.append(str(fp))

        # 3. Components
        for comp in project.components:
            fp = project_path / comp.file_path
            self._safe_write(fp, comp.code)
            files_written.append(str(fp))

        # 4. Pages
        for page in project.pages:
            fp = project_path / page.file_path
            self._safe_write(fp, page.code)
            files_written.append(str(fp))

        # 5. README
        readme = self._readme(project)
        self._safe_write(project_path / "README.md", readme)
        files_written.append(str(project_path / "README.md"))

        logger.info("Wrote %d files to %s", len(files_written), project_path)

        return {
            "project_path": str(project_path),
            "files_created": files_written,
            "structure": project.structure,
        }

    def write_single_file(self, file_path: str, code: str) -> str:
        fp = Path(file_path)
        self._safe_write(fp, code)
        return str(fp)

    def get_project_path(self, project_name: str) -> Path:
        return self.output_dir / project_name

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _safe_write(fp: Path, content: str) -> None:
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    # ------------------------------------------------------------------
    # Scaffold: generate boilerplate config files for a Next.js project
    # ------------------------------------------------------------------

    def _write_scaffold(self, root: Path, project: GeneratedProject) -> None:
        self._write_package_json(root, project)
        self._write_tsconfig(root)
        self._write_tailwind_config(root)
        self._write_postcss_config(root)
        self._write_next_config(root)
        self._write_app_layout(root, project)
        self._write_globals_css(root)
        self._write_gitignore(root)

    # --- package.json ---
    @staticmethod
    def _write_package_json(root: Path, project: GeneratedProject) -> None:
        pkg = {
            "name": project.project_name,
            "version": "0.1.0",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "lint": "next lint",
            },
            "dependencies": {
                "react": "^18.3.0",
                "react-dom": "^18.3.0",
                "next": "^14.2.0",
            },
            "devDependencies": {
                "typescript": "^5.4.0",
                "@types/node": "^20.12.0",
                "@types/react": "^18.3.0",
                "@types/react-dom": "^18.3.0",
                "autoprefixer": "^10.4.19",
                "postcss": "^8.4.38",
                "tailwindcss": "^3.4.3",
                "eslint": "^8.57.0",
                "eslint-config-next": "^14.2.0",
            },
        }
        (root / "package.json").write_text(
            json.dumps(pkg, indent=2) + "\n", encoding="utf-8"
        )

    # --- tsconfig.json ---
    @staticmethod
    def _write_tsconfig(root: Path) -> None:
        ts = {
            "compilerOptions": {
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./*"]},
            },
            "include": [
                "next-env.d.ts",
                "**/*.ts",
                "**/*.tsx",
                ".next/types/**/*.ts",
            ],
            "exclude": ["node_modules"],
        }
        (root / "tsconfig.json").write_text(
            json.dumps(ts, indent=2) + "\n", encoding="utf-8"
        )

    # --- tailwind.config.ts ---
    @staticmethod
    def _write_tailwind_config(root: Path) -> None:
        cfg = """\
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
"""
        (root / "tailwind.config.ts").write_text(cfg, encoding="utf-8")

    # --- postcss.config.js ---
    @staticmethod
    def _write_postcss_config(root: Path) -> None:
        cfg = """\
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""
        (root / "postcss.config.js").write_text(cfg, encoding="utf-8")

    # --- next.config.js ---
    @staticmethod
    def _write_next_config(root: Path) -> None:
        cfg = """\
/** @type {import('next').NextConfig} */
const nextConfig = {};

module.exports = nextConfig;
"""
        (root / "next.config.js").write_text(cfg, encoding="utf-8")

    # --- app/layout.tsx ---
    @staticmethod
    def _write_app_layout(root: Path, project: GeneratedProject) -> None:
        title = project.project_name.replace("-", " ").title()
        layout = f'''\
import type {{ Metadata }} from "next";
import {{ Inter }} from "next/font/google";
import "./globals.css";

const inter = Inter({{ subsets: ["latin"] }});

export const metadata: Metadata = {{
  title: "{title}",
  description: "Frontend project generated by AI Frontend Developer Agent",
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="en">
      <body className={{inter.className}}>{{children}}</body>
    </html>
  );
}}
'''
        app_dir = root / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "layout.tsx").write_text(layout, encoding="utf-8")

    # --- app/globals.css ---
    @staticmethod
    def _write_globals_css(root: Path) -> None:
        css = """\
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground: #171717;
  --background: #ffffff;
}

@media (prefers-color-scheme: dark) {
  :root {
    --foreground: #ededed;
    --background: #0a0a0a;
  }
}

html,
body {
  margin: 0;
  padding: 0;
  color: var(--foreground);
  background: var(--background);
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
"""
        app_dir = root / "app"
        app_dir.mkdir(parents=True, exist_ok=True)
        (app_dir / "globals.css").write_text(css, encoding="utf-8")

    # --- .gitignore ---
    @staticmethod
    def _write_gitignore(root: Path) -> None:
        gi = """\
node_modules/
.next/
out/
.env*.local
*.tsbuildinfo
next-env.d.ts
"""
        (root / ".gitignore").write_text(gi, encoding="utf-8")

    # --- README.md ---
    @staticmethod
    def _readme(project: GeneratedProject) -> str:
        title = project.project_name.replace("-", " ").title()
        lines = [
            f"# {title}",
            "",
            "> Generated by **AI Frontend Developer Agent**",
            "",
            "## Overview",
            "",
            project.explanation or "_No description provided._",
            "",
            "## Tech Stack",
            "",
            "| Layer | Tech |",
            "|-------|------|",
            "| Framework | Next.js 14 (App Router) |",
            "| Language | TypeScript 5 |",
            "| Styling | TailwindCSS 3 |",
            "| Runtime | React 18 |",
            "",
            "## Quick Start",
            "",
            "```bash",
            "npm install",
            "npm run dev",
            "```",
            "",
            "Open [http://localhost:3000](http://localhost:3000) in your browser.",
            "",
            "## Project Structure",
            "",
        ]
        for item in project.structure:
            lines.append(f"- `{item}`")

        return "\n".join(lines) + "\n"
