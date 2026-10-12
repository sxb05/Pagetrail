import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import brandLogoUrl from "./assets/pagetrail-icon.png";
import {
  ArrowUp,
  ChevronDown,
  Copy,
  FileText,
  LogOut,
  Menu,
  MessageSquare,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";

type Conversation = { thread_id: string; name: string; updated_at?: string };
type ChatMessage = { role: "user" | "assistant"; content: string };

function publicErrorMessage(detail: unknown, fallback: string): string {
  const text = typeof detail === "string"
    ? detail
    : Array.isArray(detail) && detail[0] && typeof detail[0].msg === "string"
      ? detail[0].msg
      : fallback;
  if (
    /postgresql:\/\/|postgres:\/\/|DATABASE_|password|sslmode|supabase\.com:\d+/i.test(text)
  ) {
    return fallback;
  }
  return text;
}

const starterPrompts = [
  { title: "Ask my documents", text: "What are the key points in the documents I uploaded?" },
  { title: "Find an answer", text: "Search my files and explain the answer with the source." },
  { title: "Search the web", text: "Look up the latest information about a topic." },
];

function BrandLogo({ size = 20 }: { size?: number }) {
  return (
    <img
      className="brand-logo-image"
      src={brandLogoUrl}
      width={size}
      height={size}
      alt=""
      aria-hidden="true"
    />
  );
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+?\*\*|`[^`]+`)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let index = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(<strong key={`${keyPrefix}-b-${index}`}>{token.slice(2, -2)}</strong>);
    } else {
      nodes.push(<code key={`${keyPrefix}-c-${index}`}>{token.slice(1, -1)}</code>);
    }
    last = match.index + token.length;
    index += 1;
  }
  if (last < text.length) {
    nodes.push(text.slice(last));
  }
  return nodes;
}

function AssistantText({ content }: { content: string }) {
  const blocks = content.split(/```/);
  const elements: ReactNode[] = [];

  blocks.forEach((block, index) => {
    if (index % 2 === 1) {
      const newline = block.indexOf("\n");
      const code = newline === -1 ? block : block.slice(newline + 1);
      elements.push(
        <pre key={`code-${index}`} className="message-code">
          <code>{code.replace(/\n$/, "")}</code>
        </pre>,
      );
      return;
    }

    let listItems: string[] = [];
    const flushList = () => {
      if (!listItems.length) return;
      const items = listItems;
      listItems = [];
      elements.push(
        <ul key={`ul-${index}-${elements.length}`} className="message-list-items">
          {items.map((item, itemIndex) => (
            <li key={itemIndex}>{renderInline(item, `li-${index}-${itemIndex}`)}</li>
          ))}
        </ul>,
      );
    };

    block.split("\n").forEach((line, lineIndex) => {
      const bullet = line.match(/^\s*[-*]\s+(.*)$/);
      if (bullet) {
        listItems.push(bullet[1]);
        return;
      }
      flushList();
      const heading = line.match(/^(#{1,3})\s+(.*)$/);
      if (heading) {
        const Tag = (`h${heading[1].length}` as "h1" | "h2" | "h3");
        elements.push(
          <Tag key={`h-${index}-${lineIndex}`} className="message-heading">
            {renderInline(heading[2], `h-${index}-${lineIndex}`)}
          </Tag>,
        );
        return;
      }
      if (!line.trim()) return;
      elements.push(
        <p key={`p-${index}-${lineIndex}`}>{renderInline(line, `p-${index}-${lineIndex}`)}</p>,
      );
    });
    flushList();
  });

  return <div className="message-text message-text--rich">{elements}</div>;
}

const backgroundOrbs = [
  { className: "auth-orb auth-orb--amber", initial: { x: -80, y: 30 }, animate: { x: 80, y: -45 } },
  { className: "auth-orb auth-orb--violet", initial: { x: 70, y: -35 }, animate: { x: -55, y: 55 } },
  { className: "auth-orb auth-orb--rose", initial: { x: 0, y: 65 }, animate: { x: -45, y: -35 } },
];

function AuthMotionBackground() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <div className="auth-motion-background" aria-hidden="true">
      <motion.div
        className="auth-mesh"
        animate={prefersReducedMotion ? undefined : { rotate: 360, scale: [1, 1.03, 1] }}
        transition={prefersReducedMotion ? undefined : { rotate: { duration: 96, repeat: Infinity, ease: "linear" }, scale: { duration: 24, repeat: Infinity, ease: "easeInOut" } }}
      />
      {backgroundOrbs.map((orb, index) => (
        <motion.div
          className={orb.className}
          key={orb.className}
          initial={orb.initial}
          animate={prefersReducedMotion ? orb.initial : orb.animate}
          transition={prefersReducedMotion ? undefined : { duration: 18 + index * 5, repeat: Infinity, repeatType: "mirror", ease: "easeInOut", delay: index * -2 }}
        />
      ))}
    </div>
  );
}

type AuthPageProps = {
  error: string;
  isRegisterMode: boolean;
  onModeChange: (isRegisterMode: boolean) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
};

function AuthPage({ error, isRegisterMode, onModeChange, onSubmit }: AuthPageProps) {
  return (
    <main className="login-page">
      <AuthMotionBackground />
      <div className="login-noise" aria-hidden="true" />
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand">
          <span className="brand-mark"><BrandLogo size={18} /></span>
          <span>Pagetrail</span>
          <span className="login-live"><span /> Secure workspace</span>
        </div>
        <div className="login-heading">
          <div className="login-orb" aria-hidden="true"><BrandLogo size={30} /></div>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={isRegisterMode ? "register" : "login"}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
            >
              <p className="login-eyebrow">{isRegisterMode ? "Start creating" : "Welcome back"}</p>
              <h1 id="login-title">{isRegisterMode ? "Create your account" : "Your ideas, in one place."}</h1>
              <p>{isRegisterMode
                ? "Set up your private AI workspace in a few seconds."
                : "Sign in to continue your conversations, ideas, and work."}</p>
            </motion.div>
          </AnimatePresence>
        </div>
        <form className="auth-form" onSubmit={onSubmit}>
          <label className="auth-field">
            <span>Username</span>
            <span className="auth-input-wrap">
              <input type="text" name="username" autoComplete="username" required minLength={3} maxLength={255} pattern="[A-Za-z0-9_.-]+" placeholder="you@example" />
            </span>
          </label>
          <label className="auth-field">
            <span>Password</span>
            <span className="auth-input-wrap">
              <input type="password" name="password" autoComplete={isRegisterMode ? "new-password" : "current-password"} required minLength={8} maxLength={128} placeholder="At least 8 characters" />
            </span>
          </label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="login-button" type="submit">
            <span>{isRegisterMode ? "Create account" : "Continue to Pagetrail"}</span>
            <ArrowUp size={17} />
          </button>
        </form>
        <p className="auth-switch">
          {isRegisterMode ? "Already have an account?" : "New to Pagetrail?"}
          <button type="button" onClick={() => onModeChange(!isRegisterMode)}>
            {isRegisterMode ? "Log in" : "Create an account"}
          </button>
        </p>
        <p className="login-note">Private by design. Your conversations and documents belong to you.</p>
      </section>
    </main>
  );
}

function App() {

  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(() => {
    return !!localStorage.getItem("access_token");
  });

  const [username, setUsername] = useState<string>(() => {
    return localStorage.getItem("username") || "GUEST";
  });

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [model, setModel] = useState("gemini-3.1-flash-lite");
  const [error, setError] = useState("");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [fileName, setFileName] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [uploadingFile, setUploadingFile] = useState(false);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const authenticatedFetch = (input: RequestInfo | URL, init: RequestInit = {}) => {
    const headers = new Headers(init.headers);
    const token = localStorage.getItem("access_token");
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(input, { ...init, headers });
  };

  const handleAuthSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    const target = e.currentTarget as HTMLFormElement;
    const username = (target.elements.namedItem("username") as HTMLInputElement).value;
    const password = (target.elements.namedItem("password") as HTMLInputElement).value;

    try {
      if (isRegisterMode) {
        const registrationResponse = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });

        if (!registrationResponse.ok) {
          const errorData = await registrationResponse.json().catch(() => ({}));
          throw new Error(
            publicErrorMessage(
              errorData.detail,
              "Registration failed. Username might be taken.",
            ),
          );
        }
      }

      const formData = new URLSearchParams({ username, password });
      const tokenResponse = await fetch("/api/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
      });

      if (!tokenResponse.ok) {
        const errorData = await tokenResponse.json().catch(() => ({}));
        throw new Error(
          publicErrorMessage(errorData.detail, "Invalid username or password."),
        );
      }

      const data = await tokenResponse.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("username", username);
      setUsername(username);
      setIsLoggedIn(true);
      setIsRegisterMode(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    setIsLoggedIn(false);
    setConversations([]);
    setMessages([]);
    setThreadId(null);
    setAccountMenuOpen(false);
  };

  useEffect(() => {
    if (!isLoggedIn) return;
    const token = localStorage.getItem("access_token");
    fetch("/api/conversations",
     {
      headers: { "Authorization": `Bearer ${token}` }
    })
      .then((response) => {
        if (response.status === 401) {
          handleLogout(); // Token expired dynamically according to auth.py
          return [];
        }
        return response.ok ? response.json() : [];
      })
      .then((data: Conversation[]) => setConversations(data))
      .catch(() => undefined);
  }, [isLoggedIn]);

  useEffect(() => {
    if (!isLoggedIn) return;
    const sharedThreadId = new URLSearchParams(window.location.search).get("conversation");
    if (sharedThreadId && conversations.some((conversation) => conversation.thread_id === sharedThreadId)) {
      void selectConversation(sharedThreadId);
    }
  }, [conversations, isLoggedIn]);

  useEffect(() => {
  bottomRef.current?.scrollIntoView({ behavior: "smooth" });
}, [messages, loading]);


  async function selectConversation(id: string) {
    setThreadId(id);
    setSidebarOpen(false);
    setError("");
    setOpenMenuId(null);
    const response = await authenticatedFetch(`/api/conversations/${id}/messages`);
    if (response.ok) setMessages(await response.json());
  }

  async function shareConversation(conversation: Conversation) {
    const shareUrl = `${window.location.origin}/?conversation=${encodeURIComponent(conversation.thread_id)}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setError(`Share link copied for "${conversation.name}".`);
    } catch {
      setError("Could not copy the share link. Please copy the page URL manually.");
    }
    setOpenMenuId(null);
  }

  async function removeConversation(conversation: Conversation) {
    if (!window.confirm(`Delete "${conversation.name}"? This cannot be undone.`)) return;
    const response = await authenticatedFetch(`/api/conversations/${conversation.thread_id}`, { method: "DELETE" });
    if (!response.ok) {
      setError("Unable to delete this conversation.");
      return;
    }
    setConversations((current) => current.filter((item) => item.thread_id !== conversation.thread_id));
    if (threadId === conversation.thread_id) {
      setThreadId(null);
      setMessages([]);
    }
    setOpenMenuId(null);
  }

  async function newChat() {
    const response = await authenticatedFetch("/api/conversations", { method: "POST" });
    if (!response.ok) return;
    const conversation: Conversation = await response.json();
    setConversations((current) => [conversation, ...current]);
    setThreadId(conversation.thread_id);
    setMessages([]);
    setError("");
    setSidebarOpen(false);
  }

  async function submitMessage(event?: FormEvent) {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading || uploadingFile) return;
    let activeThread = threadId;
    if (!activeThread) {
      const response = await authenticatedFetch("/api/conversations", { method: "POST" });
      if (!response.ok) return;
      const conversation: Conversation = await response.json();
      activeThread = conversation.thread_id;
      setThreadId(activeThread);
      setConversations((current) => [conversation, ...current]);
    }
    setError("");
    if (pendingFile) {
      const uploaded = await uploadFile(pendingFile, activeThread);
      if (!uploaded) return;
    }
    setInput("");
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setLoading(true);
    try {
      const response = await authenticatedFetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: activeThread, message: trimmed, model }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(publicErrorMessage(data.detail, "Something went wrong."));
      }
      setMessages((current) => [...current, data]);
      setConversations((current) =>
        current.map((conversation) =>
          conversation.thread_id === activeThread
            ? { ...conversation, name: trimmed.slice(0, 48), updated_at: new Date().toISOString() }
            : conversation,
        ),
      );
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to send message.");
    } finally {
      setLoading(false);
    }
  }

  async function uploadFile(file: File, activeThread: string) {
    setUploadingFile(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await authenticatedFetch(`/api/conversations/${activeThread}/files`, { method: "POST", body: form });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          publicErrorMessage(
            errorData.detail,
            "This file could not be added to the conversation.",
          ),
        );
      }
      setPendingFile(null);
      setFileName("");
      if (fileRef.current) fileRef.current.value = "";
      return true;
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "This file could not be added to the conversation.");
      return false;
    } finally {
      setUploadingFile(false);
    }
  }
  
  if (!isLoggedIn) {
    return (
      <AuthPage
        error={error}
        isRegisterMode={isRegisterMode}
        onModeChange={(registerMode) => {
          setIsRegisterMode(registerMode);
          setError("");
        }}
        onSubmit={handleAuthSubmit}
      />
    );
  }
  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar--open" : ""}`}>
        <div className="sidebar-top">
          <button className="brand" onClick={newChat} aria-label="Start a new chat">
            <span className="brand-mark"><BrandLogo size={18} /></span>
            <span>Pagetrail</span>
          </button>
          <button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar"><X size={18} /></button>
        </div>
        <button className="new-chat" onClick={newChat}><Plus size={17} /> New chat <span className="shortcut">Ctrl K</span></button>
        <div className="sidebar-search"><Search size={16} /><input placeholder="Search chats" /></div>
        <div className="history-heading">Conversations <MoreHorizontal size={17} /></div>
        <nav className="history-list">
          {conversations.length === 0 && <p className="empty-history">Your recent conversations will appear here.</p>}
          {conversations.map((conversation) => (
            <div key={conversation.thread_id} className={`history-item ${conversation.thread_id === threadId ? "active" : ""}`}>
              <button className="history-select" onClick={() => selectConversation(conversation.thread_id)}>
                <MessageSquare size={15} /><span>{conversation.name}</span>
              </button>
              <button
                className="history-menu-button"
                aria-label={`Actions for ${conversation.name}`}
                aria-expanded={openMenuId === conversation.thread_id}
                onClick={(event) => {
                  event.stopPropagation();
                  setOpenMenuId((current) => current === conversation.thread_id ? null : conversation.thread_id);
                }}
              >
                <MoreHorizontal size={17} />
              </button>
              {openMenuId === conversation.thread_id && (
                <div className="history-menu">
                  <button onClick={() => shareConversation(conversation)}><Copy size={14} /> Share</button>
                  <button className="danger" onClick={() => removeConversation(conversation)}><X size={14} /> Delete</button>
                </div>
              )}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="account-menu-wrap">
            <button
              className="account-card"
              aria-label="Open account menu"
              aria-expanded={accountMenuOpen}
              aria-haspopup="menu"
              onClick={() => setAccountMenuOpen((current) => !current)}
            >
              <span className="avatar">{username?.trim() ? username.trim().charAt(0).toUpperCase() : "?"}</span>
              <span><strong>{username}</strong><small>Free plan</small></span>
              <MoreHorizontal size={17} />
            </button>
            {accountMenuOpen && (
              <div className="account-menu" role="menu">
                <button
                  className="danger"
                  role="menuitem"
                  onClick={handleLogout}
                >
                  <LogOut size={14} /> Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>
      {sidebarOpen && <button className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar" />}
      <main className="main-panel">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Menu size={19} /></button>
          <button className="model-picker" onClick={() => setModel(model === "gemini-3.1-flash-lite" ? "gemini-2.5-flash" : "gemini-3.1-flash-lite")}>
            <span className="status-dot" /> {model === "gemini-3.1-flash-lite" ? "Gemini Flash Lite" : "Gemini Flash"} <ChevronDown size={15} />
          </button>
          <div className="topbar-actions"><button className="icon-button" aria-label="Share chat"><MoreHorizontal size={19} /></button><button className="avatar small">{username?.trim() ? username.trim().charAt(0).toUpperCase() : "?"}</button></div>
        </header>
        <section className={`chat-stage ${messages.length ? "chat-stage--active" : ""}`}>
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="welcome-orb"><FileText size={29} /></div>
              <p className="welcome-eyebrow">Your documents, connected</p>
              <h1>What would you like to find?</h1>
              <p>Ask your files, search the web, and keep a clear trail back to the source.</p>
              <div className="prompt-grid">{starterPrompts.map((prompt) => <button key={prompt.title} className="prompt-card" onClick={() => setInput(prompt.text)}><span>{prompt.title}</span><small>{prompt.text}</small><ArrowUp size={15} /></button>)}</div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((message, index) => <Message key={`${message.role}-${index}`} message={message} />)}
              {loading && <div className="message-row assistant"><div className="assistant-avatar"><BrandLogo size={15} /></div><div className="typing"><i /><i /><i /></div></div>}
              <div ref={bottomRef} />
            </div>
          )}
          {error && <div className="error-banner">{error}</div>}
          <form className="composer-wrap" onSubmit={submitMessage}>
            {fileName && <div className={`file-chip ${uploadingFile ? "file-chip--uploading" : ""}`}><FileText size={14} /> <span>{fileName}</span>{uploadingFile && <span className="file-chip-status">Uploading...</span>}<button type="button" onClick={() => { setPendingFile(null); setFileName(""); if (fileRef.current) fileRef.current.value = ""; }} disabled={uploadingFile}><X size={13} /></button></div>}
            <div className="composer">
              <input ref={fileRef} type="file" accept=".pdf,.docx,.txt,.md" hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) { setPendingFile(file); setFileName(file.name); setError(""); } }} />
              <button type="button" className="composer-button" onClick={() => fileRef.current?.click()} aria-label="Attach file"><Paperclip size={19} /></button>
              <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask your documents or search the web..." aria-label="Ask your documents or search the web" />
              <button className={`send-button ${input.trim() ? "send-button--ready" : ""}`} aria-label="Send message" disabled={!input.trim() || loading}><ArrowUp size={17} /></button>
            </div>
            <p className="composer-note">Pagetrail can search your files and the web. Check important information.</p>
          </form>
        </section>
      </main>
    </div>
  );
}

function Message({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return <div className={`message-row ${isUser ? "user" : "assistant"}`}>
    {isUser ? <div className="avatar message-avatar">s</div> : <div className="assistant-avatar"><BrandLogo size={15} /></div>}
    <div className="message-content"><div className="message-role">{isUser ? "You" : "Pagetrail"}</div>{isUser ? <div className="message-text">{message.content}</div> : <AssistantText content={message.content} />}{!isUser && <div className="message-actions"><button aria-label="Copy response"><Copy size={14} /></button><button aria-label="Good response"><ThumbsUp size={14} /></button><button aria-label="Bad response"><ThumbsDown size={14} /></button></div>}</div>
  </div>;
}

export default App;
