# PageTrail

Document-aware chat with retrieval, web search, and long-term memory.

**Live demo:** [https://pagetrail.onrender.com](https://pagetrail.onrender.com)

PageTrail is a FastAPI + React app. You can chat with uploaded PDFs, DOCX, TXT, and Markdown files, search the web, and keep conversation history across sessions. Application data and document embeddings live in Supabase PostgreSQL. Chat uses Google Gemini; optional web search uses Tavily.

## Features

- Sign in and keep conversations per user
- Upload documents and ask questions grounded in those files
- Web search when a question needs current information
- Long-term memory for facts the user asks the assistant to remember
- Conversation list, message history, and a production frontend served by the API

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, TypeScript |
| Backend | FastAPI, LangGraph, LangChain |
| Models | Google Gemini |
| Database | Supabase PostgreSQL |
| Search | Tavily (optional) |
| Local extras | Redis (optional supporting service) |
| Hosted app | [Render](https://pagetrail.onrender.com) |

The project does not require the PostgreSQL `vector` extension. Embeddings are stored as JSON and ranked with cosine similarity in the backend.

## Project layout

```text
backend/app/           FastAPI application package
  api/routes/          Auth, chat, and health routes
  core/                Settings and filesystem paths
  db/                  SQLAlchemy models and session helpers
  schemas/             Pydantic request and response models
  services/            LangGraph agent, RAG, and tools
frontend/              React + Vite client
notebooks/             Exploratory notebooks
```

The Docker image copies `backend/` and the built `frontend/dist` into the container and starts `uvicorn app.main:app`.

## Requirements

- Python 3.11 or newer
- Node.js and npm
- A Supabase project
- A Gemini API key
- A Tavily API key if web search is enabled

## Environment

Create a `.env` file in the repository root. Never commit this file.

Use the Supabase database URI from:

**Supabase Dashboard → Project Settings → Database → Connection string → URI → Session pooler**

Example shape:

```env
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

GEMINI_API_KEY=your-gemini-key
TAVILY_API_KEY=your-tavily-key

SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_SECRET_KEY=your-secret-key
SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json

SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

`DATABASE_URL` is preferred. The legacy `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USERNAME`, and `DATABASE_PASSWORD` variables remain supported as a local PostgreSQL fallback.

If the database password contains special characters, use the exact URI copied from Supabase or URL-encode the password.

For a hosted deployment (for example Render), set the same variables in the service environment. The Docker image listens on port `8000`.

## Install dependencies

From PowerShell:

```powershell
conda activate multi-agents
pip install -r .\backend\requirements.txt
npm --prefix .\frontend install
```

## Database setup

The application creates the required tables on startup:

- `users`
- `conversations`
- `chat_messages`
- `long_term_memory`
- `rag_documents`

Row-level security is enabled on all public application tables. The FastAPI backend connects using the database URL and performs application authorization checks.

## Run the application

### Docker

Docker runs the API and the built React frontend together:

- `app`: FastAPI backend serving `frontend/dist`
- `redis`: Redis supporting service
- Supabase PostgreSQL: external database via `DATABASE_URL`

Make sure `.env` exists in the repository root before starting Compose. It is passed to the application container and is not copied into the image.

```powershell
docker compose up --build -d
docker compose logs -f app
```

Open [http://localhost:8000](http://localhost:8000).

```powershell
docker compose down
```

The database remains in Supabase when containers are stopped. Do not add a local PostgreSQL container unless you want a separate database from Supabase.

### Local development

Start Redis if it is needed:

```powershell
docker compose up -d redis
```

Backend:

```powershell
conda activate multi-agents
uvicorn app.main:app --reload --app-dir backend
```

Frontend:

```powershell
npm --prefix .\frontend run dev
```

The backend runs at `http://127.0.0.1:8000` and the frontend at `http://localhost:5173`.

Production frontend build:

```powershell
npm --prefix .\frontend run build
```

The backend serves `frontend/dist` when that directory exists.

## Document RAG flow

1. Select a PDF, DOCX, TXT, or Markdown file in the composer.
2. The file is staged locally and is not uploaded immediately.
3. Press **Send**.
4. The backend uploads and extracts the file.
5. Text is split into chunks and embeddings are stored in `public.rag_documents`.
6. Relevant chunks for the current conversation are retrieved from PostgreSQL and included in the LLM context.

## Useful checks

Health endpoint:

```text
GET http://127.0.0.1:8000/api/health
```

On the live deployment:

```text
GET https://pagetrail.onrender.com/api/health
```

Database connection:

```powershell
python -m app.db.session
```

Run that command from the `backend` directory so Python can import the `app` package.

Frontend build:

```powershell
npm --prefix .\frontend run build
```

## Security notes

- Do not commit `.env`.
- Do not expose `SUPABASE_SECRET_KEY` in frontend code.
- Rotate database and API credentials if they have been shared publicly.
- Use the Supabase Session Pooler URI when the direct database hostname cannot be resolved by the local network.
