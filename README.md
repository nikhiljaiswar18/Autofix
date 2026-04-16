# AutoFix AI — Automated Code Tester & Fixer

An LLM-powered tool that automatically detects bugs, security vulnerabilities, and code style issues in your code, then fixes them for you.

## Features

- **Multi-Language Support** — Python, JavaScript/TypeScript, Java, C/C++, Go
- **3-Phase Analysis** — Bug detection, security audit, code style review (runs in parallel)
- **Auto-Fix** — Generates a fully corrected file with all issues resolved
- **Live Progress** — Real-time step-by-step progress via Server-Sent Events (SSE)
- **Code Quality Grade** — A+ to F grade with animated score ring
- **Diff View** — Line-by-line comparison (red = removed, green = added)
- **PDF Report** — Download a professional PDF report of all findings
- **Copy & Download** — One-click copy or download of the fixed code

## Tech Stack

- **Backend:** FastAPI (Python)
- **Frontend:** HTML / CSS / JavaScript (served by FastAPI)
- **LLM:** OpenRouter API (free models — GPT-OSS, Nemotron, Gemma)
- **PDF:** fpdf2

## Prerequisites

- Python 3.10 or higher
- An OpenRouter API key (free at [openrouter.ai](https://openrouter.ai))

## Setup & Run

### 1. Install dependencies

```bash
cd autofix-ai
pip install -r requirements.txt
```

### 2. Configure API key

Open the `.env` file and replace the placeholder with your OpenRouter API key:

```
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

You can get a free API key at https://openrouter.ai/settings/keys

### 3. Start the server

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 4. Open in browser

Go to **http://localhost:8000**

### 5. Use it

1. Drag & drop (or browse) any supported code file
2. Click **"Analyze & Fix"**
3. Wait ~20-40 seconds for the AI to analyze
4. View issues by category (Bugs / Security / Style)
5. Check the **Diff View** tab to see exactly what changed
6. **Copy** or **Download** the fixed code
7. Optionally download a **PDF Report**

## Supported File Types

| Language       | Extensions                          |
|----------------|-------------------------------------|
| Python         | `.py`                               |
| JavaScript/TS  | `.js`, `.jsx`, `.ts`, `.tsx`         |
| Java           | `.java`                             |
| C/C++          | `.c`, `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp` |
| Go             | `.go`                               |

## Project Structure

```
autofix-ai/
├── .env                    # API key configuration
├── requirements.txt        # Python dependencies
├── main.py                 # FastAPI server + API endpoints
├── analyzer/
│   ├── __init__.py
│   ├── llm_client.py       # OpenRouter API wrapper with model fallback
│   ├── prompts.py          # Language-specific analysis prompts
│   ├── code_analyzer.py    # Analysis pipeline orchestrator
│   └── report.py           # PDF report generator
├── static/
│   ├── index.html          # Frontend UI
│   ├── style.css           # Dark theme styling
│   └── script.js           # File upload, SSE streaming, diff view, grade ring
├── test_files/             # Sample buggy files for testing
│   ├── test_login.py
│   ├── test_calculator.py
│   ├── test_filemanager.py
│   ├── test_buggy.js
│   └── test_buggy.java
└── uploads/                # Temporary upload directory
```

## API Endpoints

| Method | Endpoint                      | Description                        |
|--------|-------------------------------|------------------------------------|
| GET    | `/`                           | Serve frontend                     |
| GET    | `/api/health`                 | Health check                       |
| GET    | `/api/languages`              | List supported languages           |
| POST   | `/api/analyze`                | Upload & analyze (JSON response)   |
| POST   | `/api/analyze-stream`         | Upload & get job ID for SSE        |
| GET    | `/api/analyze-stream/{id}`    | SSE stream with live progress      |
| POST   | `/api/report`                 | Upload & get PDF report            |

## Troubleshooting

- **"All models failed"** — Your API key may be invalid or all free models are rate-limited. Wait a minute and retry.
- **0 issues found** — The LLM call may have been rate-limited. Check terminal logs for 429 errors.
- **Port already in use** — Kill the existing process: `fuser -k 8000/tcp` (Linux/Mac) or find the PID via `netstat -ano | findstr :8000` and `taskkill /F /PID <pid>` (Windows).
