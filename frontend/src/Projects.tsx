import { useEffect, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  FolderKanban,
  ListChecks,
  Plus,
  Search,
  Users,
} from "lucide-react";

type Organization = { id: number; name: string; slug: string };
type Project = {
  id: number;
  organization_id: number;
  name: string;
  description?: string | null;
  status: string;
  updated_at: string;
};
type Task = {
  id: number;
  project_id: number;
  title: string;
  status: string;
  priority: string;
  assignee_id?: number | null;
  due_date?: string | null;
  milestone_id?: number | null;
};
type Milestone = {
  id: number;
  title: string;
  status: string;
  due_date?: string | null;
  description?: string | null;
};

type Props = {
  authenticatedFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
  navigate: (path: string) => void;
  username: string;
};

export default function Projects({ authenticatedFetch, navigate, username }: Props) {
  const pathParts = window.location.pathname.split("/").filter(Boolean);
  const projectId = pathParts[1] ? Number(pathParts[1]) : null;
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [metrics, setMetrics] = useState({ active_projects: 0, total_tasks: 0, completed_tasks: 0, overdue_tasks: 0, blocked_tasks: 0 });
  const [activeTab, setActiveTab] = useState("overview");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [showCreateTask, setShowCreateTask] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [orgRes, projectRes, metricsRes] = await Promise.all([
          authenticatedFetch("/api/organizations"),
          authenticatedFetch("/api/projects"),
          authenticatedFetch("/api/projects/overview/metrics"),
        ]);
        if (!orgRes.ok || !projectRes.ok) throw new Error("Unable to load project workspace.");
        setOrganizations(await orgRes.json());
        setProjects(await projectRes.json());
        if (metricsRes.ok) setMetrics(await metricsRes.json());
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to load projects.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [authenticatedFetch]);

  useEffect(() => {
    if (!projectId) return;
    const loadProject = async () => {
      setLoading(true);
      setError("");
      try {
        const [projectRes, tasksRes, milestonesRes] = await Promise.all([
          authenticatedFetch(`/api/projects/${projectId}`),
          authenticatedFetch(`/api/projects/${projectId}/tasks`),
          authenticatedFetch(`/api/projects/${projectId}/milestones`),
        ]);
        if (!projectRes.ok) throw new Error("Project not found or access denied.");
        setProject(await projectRes.json());
        setTasks(tasksRes.ok ? await tasksRes.json() : []);
        setMilestones(milestonesRes.ok ? await milestonesRes.json() : []);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to load project.");
      } finally {
        setLoading(false);
      }
    };
    void loadProject();
  }, [projectId, authenticatedFetch]);

  const createOrganization = async (name: string) => {
    const response = await authenticatedFetch("/api/organizations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!response.ok) throw new Error("Unable to create organization.");
    return response.json() as Promise<Organization>;
  };

  const handleCreateProject = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    let organizationId = Number(data.get("organization_id"));
    if (!organizationId) {
      const name = String(data.get("organization_name") || "").trim();
      if (!name) return;
      try {
        const organization = await createOrganization(name);
        organizationId = organization.id;
        setOrganizations((current) => [...current, organization]);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to create organization.");
        return;
      }
    }
    const response = await authenticatedFetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        organization_id: organizationId,
        name: String(data.get("name")),
        description: String(data.get("description") || ""),
        status: "active",
      }),
    });
    if (!response.ok) {
      setError("Unable to create project.");
      return;
    }
    const created = await response.json();
    setProjects((current) => [created, ...current]);
    setShowCreateProject(false);
  };

  const handleCreateTask = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!projectId) return;
    const data = new FormData(event.currentTarget);
    const response = await authenticatedFetch(`/api/projects/${projectId}/tasks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: String(data.get("title")),
        description: String(data.get("description") || ""),
        status: String(data.get("status") || "todo"),
        priority: String(data.get("priority") || "medium"),
        milestone_id: data.get("milestone_id") ? Number(data.get("milestone_id")) : null,
        due_date: data.get("due_date") ? new Date(String(data.get("due_date"))).toISOString() : null,
      }),
    });
    if (!response.ok) {
      setError("Unable to create task.");
      return;
    }
    const createdTask = await response.json();
    setTasks((current) => [createdTask, ...current]);
    setShowCreateTask(false);
  };

  const updateTaskStatus = async (taskId: number, status: string) => {
    const response = await authenticatedFetch(`/api/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (!response.ok) {
      setError("Unable to update task.");
      return;
    }
    const updated = await response.json();
    setTasks((current) => current.map((task) => task.id === taskId ? updated : task));
  };

  const visibleProjects = projects.filter((item) =>
    item.name.toLowerCase().includes(search.toLowerCase()) ||
    (item.description || "").toLowerCase().includes(search.toLowerCase()),
  );

  if (projectId) {
    const completed = tasks.filter((task) => task.status === "done").length;
    const progress = tasks.length ? Math.round((completed / tasks.length) * 100) : 0;
    return (
      <main className="operations-shell">
        <header className="operations-topbar">
          <button className="operations-back" onClick={() => navigate("/projects")}><ArrowLeft size={16} /> Projects</button>
          <span className="operations-user">{username}</span>
        </header>
        {loading ? (
          <div className="operations-state">Loading project…</div>
        ) : error ? (
          <div className="operations-state operations-error">{error}</div>
        ) : project ? (
          <div className="project-workspace">
            <header className="project-header">
              <div>
                <p className="operations-kicker">Project workspace</p>
                <h1>{project.name}</h1>
                <p>{project.description || "No project description yet."}</p>
              </div>
              <button className="operations-primary" onClick={() => setShowCreateTask(true)}><Plus size={16} /> New task</button>
            </header>
            <nav className="project-tabs" aria-label="Project sections">
              {["overview", "tasks", "milestones", "members", "knowledge"].map((tab) => (
                <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>
                  {tab[0].toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </nav>
            {activeTab === "overview" && (
              <div className="project-overview">
                <section className="progress-card">
                  <div className="progress-ring" style={{ "--progress": `${progress}%` } as CSSProperties}>
                    <strong>{progress}%</strong>
                  </div>
                  <div><p>Task completion</p><h2>{completed} of {tasks.length} complete</h2></div>
                </section>
                <section className="operations-grid">
                  <article><CircleAlert size={18} /><span>Blocked</span><strong>{tasks.filter((task) => task.status === "blocked").length}</strong></article>
                  <article><CalendarDays size={18} /><span>Milestones</span><strong>{milestones.length}</strong></article>
                  <article><CheckCircle2 size={18} /><span>Completed</span><strong>{completed}</strong></article>
                </section>
                <section className="operations-panel">
                  <h2>Recently updated tasks</h2>
                  {tasks.length === 0 ? <p className="operations-empty">No tasks yet.</p> : tasks.slice(0, 8).map((task) => (
                    <button className="task-row" key={task.id} onClick={() => setActiveTab("tasks")}>
                      <span>{task.title}</span><span className={`status status-${task.status}`}>{task.status.replace("_", " ")}</span>
                    </button>
                  ))}
                </section>
              </div>
            )}
            {activeTab === "tasks" && (
              <section className="operations-panel">
                <div className="operations-panel-header"><h2>Tasks</h2><button onClick={() => setShowCreateTask(true)}><Plus size={15} /> Add task</button></div>
                {tasks.length === 0 ? <p className="operations-empty">No tasks in this project.</p> : (
                  <div className="task-table">
                    {tasks.map((task) => (
                      <div className="task-table-row" key={task.id}>
                        <div><strong>{task.title}</strong><small>{task.priority} priority</small></div>
                        <select value={task.status} onChange={(event) => void updateTaskStatus(task.id, event.target.value)}>
                          <option value="todo">To do</option><option value="in_progress">In progress</option><option value="blocked">Blocked</option><option value="done">Done</option>
                        </select>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            )}
            {activeTab === "milestones" && (
              <section className="operations-panel">
                <h2>Milestones</h2>
                {milestones.length === 0 ? <p className="operations-empty">No milestones yet.</p> : milestones.map((milestone) => (
                  <div className="task-row" key={milestone.id}><span>{milestone.title}</span><span className={`status status-${milestone.status}`}>{milestone.status}</span></div>
                ))}
              </section>
            )}
            {activeTab === "members" && <Members projectId={project.id} authenticatedFetch={authenticatedFetch} />}
            {activeTab === "knowledge" && <Knowledge projectId={project.id} authenticatedFetch={authenticatedFetch} />}
          </div>
        ) : null}
        {showCreateTask && (
          <Modal title="Create task" onClose={() => setShowCreateTask(false)}>
            <form className="operations-form" onSubmit={handleCreateTask}>
              <label>Title<input name="title" required /></label>
              <label>Description<textarea name="description" /></label>
              <div className="operations-form-grid">
                <label>Status<select name="status"><option value="todo">To do</option><option value="in_progress">In progress</option><option value="blocked">Blocked</option><option value="done">Done</option></select></label>
                <label>Priority<select name="priority"><option value="medium">Medium</option><option value="low">Low</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
              </div>
              <label>Milestone<select name="milestone_id" defaultValue=""><option value="">No milestone</option>{milestones.map((milestone) => <option value={milestone.id} key={milestone.id}>{milestone.title}</option>)}</select></label>
              <label>Due date<input type="datetime-local" name="due_date" /></label>
              <button className="operations-primary" type="submit">Create task</button>
            </form>
          </Modal>
        )}
      </main>
    );
  }

  return (
    <main className="operations-shell">
      <header className="operations-topbar"><button className="operations-back" onClick={() => navigate("/app")}><ArrowLeft size={16} /> Chat</button><span className="operations-user">{username}</span></header>
      <div className="projects-dashboard">
        <header className="projects-header">
          <div><p className="operations-kicker">Pagetrail workspace</p><h1>Projects</h1><p>Plan work, track milestones, and coordinate execution.</p></div>
          <button className="operations-primary" onClick={() => setShowCreateProject(true)}><Plus size={16} /> New project</button>
        </header>
        {error && <div className="operations-error">{error}</div>}
        <section className="metric-grid">
          <article><FolderKanban size={19} /><span>Active projects</span><strong>{metrics.active_projects}</strong></article>
          <article><ListChecks size={19} /><span>Total tasks</span><strong>{metrics.total_tasks}</strong></article>
          <article><CheckCircle2 size={19} /><span>Completed</span><strong>{metrics.completed_tasks}</strong></article>
          <article><CircleAlert size={19} /><span>Overdue / blocked</span><strong>{metrics.overdue_tasks} / {metrics.blocked_tasks}</strong></article>
        </section>
        <div className="projects-toolbar"><label><Search size={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search projects" /></label></div>
        {loading ? <div className="operations-state">Loading projects…</div> : visibleProjects.length === 0 ? (
          <div className="operations-empty-card"><FolderKanban size={28} /><h2>No projects yet</h2><p>Create a project to organize tasks and milestones.</p><button className="operations-primary" onClick={() => setShowCreateProject(true)}><Plus size={16} /> Create project</button></div>
        ) : (
          <section className="project-grid">
            {visibleProjects.map((item) => (
              <button className="project-card" key={item.id} onClick={() => navigate(`/projects/${item.id}`)}>
                <div className="project-card-top"><span className={`status status-${item.status}`}>{item.status}</span></div>
                <h2>{item.name}</h2><p>{item.description || "No description"}</p>
                <div className="project-card-footer"><span><Users size={14} /> Team workspace</span><span>{new Date(item.updated_at).toLocaleDateString()}</span></div>
              </button>
            ))}
          </section>
        )}
      </div>
      {showCreateProject && (
        <Modal title="Create project" onClose={() => setShowCreateProject(false)}>
          <form className="operations-form" onSubmit={handleCreateProject}>
            {organizations.length > 0 ? <label>Organization<select name="organization_id" defaultValue={organizations[0].id}>{organizations.map((organization) => <option key={organization.id} value={organization.id}>{organization.name}</option>)}</select></label> : <label>Organization name<input name="organization_name" required placeholder="My organization" /></label>}
            <label>Project name<input name="name" required /></label>
            <label>Description<textarea name="description" /></label>
            <button className="operations-primary" type="submit">Create project</button>
          </form>
        </Modal>
      )}
    </main>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="operations-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="operations-modal" role="dialog" aria-modal="true" aria-label={title}>
        <header><h2>{title}</h2><button onClick={onClose} aria-label="Close">×</button></header>
        {children}
      </section>
    </div>
  );
}

function Members({ projectId, authenticatedFetch }: { projectId: number; authenticatedFetch: Props["authenticatedFetch"] }) {
  const [members, setMembers] = useState<Array<{ id: number; user_id: number; role: string }>>([]);
  useEffect(() => {
    void authenticatedFetch(`/api/projects/${projectId}/members`).then(async (response) => {
      if (response.ok) setMembers(await response.json());
    });
  }, [projectId, authenticatedFetch]);
  return <section className="operations-panel"><h2>Members</h2>{members.length === 0 ? <p className="operations-empty">No project members found.</p> : members.map((member) => <div className="task-row" key={member.id}><span>User {member.user_id}</span><span className="status">{member.role}</span></div>)}</section>;
}

function Knowledge({ projectId, authenticatedFetch }: { projectId: number; authenticatedFetch: Props["authenticatedFetch"] }) {
  const [documents, setDocuments] = useState<Array<{ id: number; filename: string; processing_status: string }>>([]);
  const [notes, setNotes] = useState<Array<{ id: number; title: string }>>([]);
  useEffect(() => {
    void Promise.all([
      authenticatedFetch(`/api/projects/${projectId}/documents`),
      authenticatedFetch(`/api/projects/${projectId}/meeting-notes`),
    ]).then(async ([documentResponse, noteResponse]) => {
      if (documentResponse.ok) setDocuments(await documentResponse.json());
      if (noteResponse.ok) setNotes(await noteResponse.json());
    });
  }, [projectId, authenticatedFetch]);
  return (
    <section className="operations-panel">
      <h2>Project knowledge</h2>
      {documents.length === 0 && notes.length === 0 ? <p className="operations-empty">No project documents or meeting notes yet.</p> : (
        <div className="knowledge-list">
          {documents.map((document) => <div className="task-row" key={`doc-${document.id}`}><span>{document.filename}</span><span className="status">{document.processing_status}</span></div>)}
          {notes.map((note) => <div className="task-row" key={`note-${note.id}`}><span>{note.title}</span><span className="status">Meeting note</span></div>)}
        </div>
      )}
    </section>
  );
}
