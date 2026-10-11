# PageTrail

PageTrail is a document-aware chat application with:

- A FastAPI backend
- A React/Vite frontend
- PostgreSQL-backed application data and document embeddings
- Google Gemini embeddings and chat models
- Optional Redis for local supporting services

The application uses Supabase PostgreSQL as its database. PostgreSQL tables
include users, conversations, chat messages, long-term memories, and uploaded
document chunks.

## Requirements

- Python 3.11 or newer
- Node.js and npm
- A Supabase project
- A Gemini API key
- A Tavily API key if web search is enabled

## Environment

Create a `.env` file in the repository root. Never commit this file.

Use the Supabase database URI from:

**Supabase Dashboard -> Project Settings -> Database -> Connection string ->
URI -> Session pooler**

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

`DATABASE_URL` is preferred by the application. The legacy
`DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USERNAME`, and
`DATABASE_PASSWORD` variables remain supported as a local PostgreSQL fallback.

If the database password contains special characters, use the exact URI copied
from Supabase or URL-encode the password.

## Install dependencies

From PowerShell:

```powershell
conda activate multi-agents
pip install -r requirements.txt
npm --prefix .\frontend install
```

## Database setup

The application creates the required tables on startup:

- `users`
- `conversations`
- `chat_messages`
- `long_term_memory`
- `rag_documents`

Row-level security is enabled on all public application tables. The FastAPI
backend connects using the database connection and performs the application
authorization checks.

## Run the application

### Docker deployment

Docker deployment runs the complete application:

- `app`: FastAPI backend with the built React frontend
- `redis`: Redis supporting service
- Supabase PostgreSQL: external database configured through `DATABASE_URL`

Make sure `.env` exists in the repository root before starting Compose. It is
passed to the application container and is not copied into the image.

Build and start the application:

```powershell
docker compose up --build -d
```

View application logs:

```powershell
docker compose logs -f app
```

Check the application:

```text
http://localhost:8000
```

Stop the deployment:

```powershell
docker compose down
```

The database remains in Supabase when the containers are stopped or removed.
Do not add a local PostgreSQL container unless you intentionally want a
separate database from Supabase.

### Local development

Start the local Redis service separately if it is needed:

```powershell
docker compose up -d redis
```

Start the backend in one terminal:

```powershell
conda activate multi-agents
uvicorn app:app --reload
```

Start the frontend in another terminal:

```powershell
npm --prefix .\frontend run dev
```

The backend runs at `http://127.0.0.1:8000` and the frontend runs at
`http://localhost:5173`.

For a production frontend build:

```powershell
npm --prefix .\frontend run build
```

The backend serves `frontend/dist` when that directory exists.

## Document RAG flow

1. Select a PDF, DOCX, TXT, or Markdown file in the composer.
2. The file is staged locally and is not uploaded immediately.
3. Press **Send**.
4. The backend uploads and extracts the file.
5. Text is split into chunks and embeddings are stored in the Supabase
   `public.rag_documents` table.
6. Relevant chunks for the current conversation are retrieved from PostgreSQL
   and included in the LLM context.

The project does not require the PostgreSQL `vector` extension. Embeddings are
stored as JSON and ranked with cosine similarity by the backend.

## Useful checks

Health endpoint:

```text
GET http://127.0.0.1:8000/api/health
```

Check the database connection:

```powershell
python .\db.py
```

Check the frontend build:

```powershell
npm --prefix .\frontend run build
```

## Security notes

- Do not commit `.env`.
- Do not expose `SUPABASE_SECRET_KEY` in frontend code.
- Rotate database and API credentials if they have been shared publicly.
- Use the Supabase Session Pooler URI when the direct database hostname cannot
  be resolved by the local network.
