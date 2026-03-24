# Frontend Developer Agent

AI Agent for generating and modifying React/Next.js frontend code.

## Quick Start

```python
from frontend_dev_agent import create_agent

agent = create_agent(api_key="your-openai-api-key")

result = agent.build("Create a login page with email and password fields")
print(result["project_path"])
```

## API Endpoints

- `POST /api/v1/generate` - Generate frontend code
- `POST /api/v1/modify` - Modify existing code
- `POST /api/v1/bugfix` - Fix bugs in code
- `GET /api/v1/tasks` - Get task history
- `GET /api/v1/task/{task_id}` - Get specific task

## Running the Server

```bash
cd frontend_agent
pip install -r requirements.txt
export OPENAI_API_KEY="your-api-key"
python main.py
```

Server runs on http://localhost:8000
