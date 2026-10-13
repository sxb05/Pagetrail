# PageTrail

**Document-aware AI chat with retrieval, web search, and long-term memory.**

<div align="center">

[![Live Demo](https://img.shields.io/badge/Live%20Demo-PageTrail-2ea44f?style=for-the-badge)](https://pagetrail.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://supabase.com/)

**Live demo:** [pagetrail.onrender.com](https://pagetrail.onrender.com)

**Source code:** [github.com/sxb05/Pagetrail](https://github.com/sxb05/Pagetrail)

</div>

---

## 🚧 Currently Working On

- **RAG improvements:** Improving document retrieval and the quality of context supplied to the language model.
- **Backend reliability:** Refining API behavior, database connectivity, error handling, and deployment workflows.
- **Authentication and data isolation:** Strengthening user-level access controls for conversations, documents, and long-term memory.
- **Production readiness:** Improving configuration management, Docker-based development, and application reliability.

## Upcoming Improvements

- [ ] **RAG evaluation:** Measure retrieval relevance and answer faithfulness.
- [ ] **Streaming responses:** Make AI conversations more interactive.
- [ ] **Semantic caching:** Reduce redundant model calls and improve response latency.
- [ ] **Background document processing:** Improve document ingestion for larger workloads.
- [ ] **Automated testing and CI/CD:** Introduce more comprehensive tests and continuous integration.
- [ ] **Observability:** Track request latency, model usage, and retrieval performance.
- [ ] **Retrieval optimization:** Explore improvements to document chunking and similarity ranking.

*These items describe development priorities and planned improvements, not guarantees that the features are already implemented.*

---

## Overview

PageTrail is a full-stack AI application that combines document-based question answering, web search, and persistent conversational memory in one interface.

Built with **FastAPI, React, TypeScript, LangGraph, LangChain, Google Gemini, and Supabase PostgreSQL**, PageTrail allows users to interact with their documents, retrieve relevant information, and continue conversations across sessions.

Instead of relying exclusively on a language model's existing knowledge, PageTrail can retrieve relevant document content and use web search when additional information is needed.

The application supports user authentication, conversation history, document retrieval, and long-term memory for facts users ask the assistant to remember.

## Features

- **Document-aware chat:** Ask questions about uploaded PDF, DOCX, TXT, and Markdown files.
- **Retrieval-Augmented Generation (RAG):** Retrieve relevant document chunks and include them in the model's context.
- **Web search:** Use Tavily to retrieve online information when web search is enabled.
- **Long-term memory:** Persist facts users explicitly ask the assistant to remember.
- **User authentication:** Sign in and maintain user-specific conversations.
- **Conversation history:** Access previous conversations and messages across sessions.
- **Persistent storage:** Store application data and document embeddings in Supabase PostgreSQL.
- **Full-stack architecture:** Integrate a React frontend with a FastAPI backend.
- **Docker support:** Run the backend and production frontend together using Docker Compose.
- **Optional Redis:** Provide a supporting service for workflows that require it.
- **Cloud deployment:** Access the deployed application through Render.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, TypeScript |
| Backend | Python, FastAPI |
| Agent orchestration | LangGraph, LangChain |
| Language model | Google Gemini |
| Database | Supabase PostgreSQL |
| Document retrieval | Embeddings, cosine similarity |
| Web search | Tavily (optional) |
| Supporting service | Redis (optional) |
| Containerization | Docker, Docker Compose |
| Deployment | Render |

### Database and retrieval design

PageTrail stores document embeddings as JSON in PostgreSQL and ranks them using cosine similarity in the backend.

The application does **not** require the PostgreSQL `vector` extension.

---

## Architecture

```mermaid
flowchart TD
    U[User] --> FE[React + Vite + TypeScript]
    FE --> API[FastAPI Backend]

    API --> AUTH[Authentication and Authorization]
    API --> AGENT[LangGraph / LangChain]

    AGENT --> LLM[Google Gemini]
    AGENT --> SEARCH[Tavily Web Search]
    AGENT --> RAG[Document Retrieval]

    RAG --> EMB[Embeddings and Cosine Similarity]
    EMB --> DB[(Supabase PostgreSQL)]

    API --> DB

    DB --> DOCS[Document Chunks and Embeddings]
    DB --> CONV[Conversations and Messages]
    DB --> MEM[Long-Term Memory]

    API --> RESP[API Response]
    RESP --> FE
```

### Request lifecycle

1. The user submits a message through the React frontend.
2. FastAPI receives the request and applies the relevant authentication and authorization checks.
3. The agent workflow coordinates the available model and retrieval operations.
4. Depending on the request, the application uses Gemini, document retrieval, or Tavily web search.
5. Retrieved information is incorporated into the model context where applicable.
6. The response is returned to the frontend, and conversation data is persisted in PostgreSQL.

The exact tools used depend on the question and the application's configured workflow.

---

## Requirements

Before running PageTrail locally, make sure you have:

- Python 3.11 or newer
- Node.js and npm
- A Supabase project with PostgreSQL enabled
- A Google Gemini API key
- A Tavily API key if web search is enabled
- Docker and Docker Compose for containerized execution

Redis is optional unless required by the functionality you are running.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/sxb05/Pagetrail.git
cd Pagetrail
```

### 2. Install backend dependencies

If you use the existing Conda environment:

```powershell
conda activate multi-agents
pip install -r requirements.txt
```

Alternatively, create a virtual environment.

**Windows PowerShell**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Install frontend dependencies

From the repository root:

```powershell
npm --prefix .\frontend install
```

---

## Environment Configuration

Create a `.env` file in the repository root. **Never commit this file to GitHub.**

Obtain your PostgreSQL connection URI from:

**Supabase Dashboard → Project Settings → Database → Connection string → URI → Session pooler**

Configure the following variables using your own credentials:

```dotenv
DATABASE_URL=postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres

GEMINI_API_KEY=your-gemini-api-key
TAVILY_API_KEY=your-tavily-api-key

SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
SUPABASE_SECRET_KEY=your-secret-key
SUPABASE_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json

SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Important:** These are example values. Use the exact variable names expected by your application's configuration. Do not commit actual credentials.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL database connection |
| `GEMINI_API_KEY` | Authentication for Google Gemini |
| `TAVILY_API_KEY` | Enables Tavily web search |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key, where used |
| `SUPABASE_SECRET_KEY` | Server-side Supabase secret, where used |
| `SUPABASE_JWKS_URL` | JSON Web Key Set endpoint, where used |
| `SECRET_KEY` | Application signing secret, where used |
| `ALGORITHM` | Token signing algorithm, where used |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration configuration, where used |

The legacy database variables remain supported as a local PostgreSQL fallback:

```dotenv
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=your_database
DATABASE_USERNAME=your_username
DATABASE_PASSWORD=your_password
```

Use `DATABASE_URL` when connecting to Supabase.

If the database password contains special characters, copy the connection URI directly from Supabase or URL-encode the password correctly.

**Security:** Never expose `SUPABASE_SECRET_KEY`, database credentials, or `SECRET_KEY` in frontend code.

---

## 🗄️ Database Setup

The application creates the required tables on startup.

| Table | Purpose |
|---|---|
| `users` | User-related application data |
| `conversations` | Conversation records |
| `chat_messages` | Conversation messages |
| `long_term_memory` | Persisted user-requested memories |
| `rag_documents` | Document chunks and embeddings |

The database is hosted on Supabase PostgreSQL.

Row-level security is enabled on the public application tables. The backend also performs application-level authorization checks.

Correct user isolation depends on the actual database policies and backend authorization logic. Both should be maintained and tested.

---

## 🐳 Running with Docker Compose

Docker Compose runs the FastAPI backend and the built React frontend together.

The expected services are:

- **`app`:** FastAPI backend serving the production frontend from `frontend/dist`.
- **`redis`:** Optional supporting service.
- **Supabase PostgreSQL:** External database accessed through `DATABASE_URL`.

Ensure the root `.env` file exists before starting the application.

Build and start the services:

```powershell
docker compose up --build -d
```

View application logs:

```powershell
docker compose logs -f app
```

Open the application:

**http://localhost:8000**

Stop the containers:

```powershell
docker compose down
```

Stopping the containers does not delete data stored in Supabase PostgreSQL.

You do not need a local PostgreSQL container when using the configured Supabase database.

---

## 💻 Local Development

### Start Redis (optional)

If Redis is required by your development workflow:

```powershell
docker compose up -d redis
```

### Start the backend

From the repository root:

```powershell
conda activate multi-agents
uvicorn app:app --reload
```

The backend will be available at:

**http://127.0.0.1:8000**

### Start the frontend

Open a separate terminal and run:

```powershell
npm --prefix .\frontend run dev
```

The Vite development server will typically be available at:

**http://localhost:5173**

### Build the production frontend

```powershell
npm --prefix .\frontend run build
```

The production frontend is generated in `frontend/dist`. When that directory exists, the backend serves the built frontend according to the application's static-file configuration.

---

## Document RAG Workflow

PageTrail supports document-based question answering through a retrieval pipeline.

1. Select a PDF, DOCX, TXT, or Markdown file in the chat composer.
2. The selected file is staged locally rather than immediately uploaded.
3. Press **Send** to submit the message and selected file.
4. The backend receives the file and extracts its text.
5. The extracted content is split into smaller chunks.
6. Embeddings are generated and stored in `public.rag_documents`.
7. Relevant chunks are retrieved using cosine similarity.
8. The retrieved context is included in the language model request to help generate a grounded answer.

The retrieval pipeline uses PostgreSQL for persistence and backend-side similarity ranking rather than requiring the PostgreSQL `vector` extension.

---

## ✅ Useful Checks

### Health endpoint

Local:

```http
GET http://127.0.0.1:8000/api/health
```

Production:

```http
GET https://pagetrail.onrender.com/api/health
```

### Check database connectivity

```powershell
python .\db.py
```

### Verify the frontend build

```powershell
npm --prefix .\frontend run build
```

### Troubleshoot deployment

If the deployed application fails to start or database-dependent requests fail:

1. Check the Render application logs.
2. Verify that the production environment variables are configured.
3. Confirm that Supabase PostgreSQL is reachable from the deployment.
4. Check the database connection URI and credentials.
5. Verify that the required tables are initialized.
6. Confirm that the frontend production build exists and is served correctly.

---

## ☁️ Deployment

PageTrail is deployed on Render.

**Live demo:** [https://pagetrail.onrender.com](https://pagetrail.onrender.com)

To deploy your own instance:

1. Push the project to a GitHub repository.
2. Create a Render Web Service connected to the repository.
3. Configure the appropriate build and start commands, or deploy using the existing Docker configuration.
4. Add the required environment variables through Render's service settings.
5. Configure the Supabase PostgreSQL connection.
6. Ensure the application listens on the expected port (`8000` in the provided Docker setup).
7. Deploy and verify the health endpoint.

Keep production credentials in Render's environment-variable settings rather than in the repository.

---

## 🛡️ Security Considerations

- Never commit `.env` files or production credentials.
- Never expose `SUPABASE_SECRET_KEY` in frontend code.
- Keep database and API credentials private.
- Rotate credentials immediately if they have been exposed.
- Enforce user-level authorization for conversations, documents, and long-term memory.
- Validate uploaded files and enforce appropriate size limits.
- Verify Supabase row-level security policies alongside backend authorization.
- Use HTTPS for production traffic.
- Avoid logging secrets, authentication tokens, or sensitive document contents.

---

## Future Improvements

Potential directions for further development include:

- Automated RAG evaluation for retrieval relevance and answer faithfulness.
- Streaming responses for a more interactive chat experience.
- Semantic caching to reduce redundant model calls.
- Background document ingestion for larger files and workloads.
- Improved observability for latency, token usage, and tool execution.
- Automated testing and continuous integration.
- More granular document permissions and retrieval controls.

---

## What This Project Demonstrates

PageTrail brings together several practical AI and software engineering concepts:

- Agent orchestration with LangGraph and LangChain.
- Retrieval-Augmented Generation and document processing.
- Integration with external language models and web search tools.
- Persistent conversational state and relational data modeling.
- Authentication and authorization in a full-stack application.
- REST API development with FastAPI.
- React and TypeScript frontend development.
- Docker-based deployment and cloud-hosted PostgreSQL.

The project explores how an AI application can combine language models with retrieved knowledge, persistent state, and external tools in a deployable full-stack system.

---

## 👨‍💻 Author

**Subash Balaji**

- GitHub: [@sxb05](https://github.com/sxb05)
- Repository: [Pagetrail](https://github.com/sxb05/Pagetrail)
- Live application: [pagetrail.onrender.com](https://pagetrail.onrender.com)

---

If you find PageTrail interesting, try the live demo or explore the source code.

