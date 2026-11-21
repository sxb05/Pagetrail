import { useEffect, useState } from "react";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  FolderKanban,
  LayoutList,
  MessageSquare,
  Plus,
  ShieldCheck,
} from "lucide-react";

type Metrics = {
  active_projects: number;
  total_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  blocked_tasks: number;
};

type Project = {
  id: number;
  organization_id: number;
  name: string;
  description?: string | null;
  status: string;
  updated_at: string;
};

type Props = {
  authenticatedFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
  navigate: (path: string) => void;
  username: string;
};

export default function Overview({ authenticatedFetch, navigate, username }: Props) {
  const [metrics, setMetrics] = useState<Metrics>({
    active_projects: 0,
    total_tasks: 0,
    completed_tasks: 0,
    overdue_tasks: 0,
    blocked_tasks: 0,
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [metricsResponse, projectsResponse] = await Promise.all([
          authenticatedFetch("/api/projects/overview/metrics"),
          authenticatedFetch("/api/projects"),
        ]);
        if (!metricsResponse.ok || !projectsResponse.ok) {
          throw new Error("Unable to load operations overview.");
        }
        setMetrics(await metricsResponse.json());
        setProjects(await projectsResponse.json());
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : "Unable to load overview.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [authenticatedFetch]);

  const completion = metrics.total_tasks
    ? Math.round((metrics.completed_tasks / metrics.total_tasks) * 100)
    : 0;

  return (
    <main className="operations-shell overview-shell">
      <header className="operations-topbar">
        <button className="operations-back" onClick={() => navigate("/app")}>
          <MessageSquare size={16} /> Chat
        </button>
        <span className="operations-user">{username}</span>
      </header>

      <div className="overview-dashboard">
        <header className="overview-header">
          <div>
            <p className="operations-kicker">Operations overview</p>
            <h1>Good morning, {username}</h1>
            <p>See the work that needs attention across your projects.</p>
          </div>
          <button className="operations-primary" onClick={() => navigate("/projects")}>
            <Plus size={16} /> Open projects
          </button>
        </header>

        {error && <div className="operations-error">{error}</div>}

        {loading ? (
          <div className="operations-state">Loading operations overview…</div>
        ) : (
          <>
            <section className="overview-metrics" aria-label="Project metrics">
              <article>
                <span><FolderKanban size={18} /> Active projects</span>
                <strong>{metrics.active_projects}</strong>
                <small>Current active workspaces</small>
              </article>
              <article>
                <span><LayoutList size={18} /> Total tasks</span>
                <strong>{metrics.total_tasks}</strong>
                <small>{completion}% completed</small>
              </article>
              <article>
                <span><CheckCircle2 size={18} /> Completed</span>
                <strong>{metrics.completed_tasks}</strong>
                <small>Tasks marked done</small>
              </article>
              <article className={metrics.overdue_tasks || metrics.blocked_tasks ? "attention" : ""}>
                <span><CircleAlert size={18} /> Needs attention</span>
                <strong>{metrics.overdue_tasks + metrics.blocked_tasks}</strong>
                <small>{metrics.overdue_tasks} overdue · {metrics.blocked_tasks} blocked</small>
              </article>
            </section>

            <section className="overview-grid">
              <div className="overview-panel project-health">
                <header>
                  <div>
                    <p>Project health</p>
                    <h2>Work distribution</h2>
                  </div>
                  <span>{completion}% complete</span>
                </header>
                <div className="health-progress">
                  <span style={{ width: `${completion}%` }} />
                </div>
                <div className="health-breakdown">
                  <div><span className="health-dot complete" /><strong>{metrics.completed_tasks}</strong><small>Completed</small></div>
                  <div><span className="health-dot blocked" /><strong>{metrics.blocked_tasks}</strong><small>Blocked</small></div>
                  <div><span className="health-dot overdue" /><strong>{metrics.overdue_tasks}</strong><small>Overdue</small></div>
                </div>
              </div>

              <div className="overview-panel quick-actions">
                <header><div><p>Quick actions</p><h2>Move work forward</h2></div></header>
                <button onClick={() => navigate("/projects")}><Plus size={16} /><span><strong>Create or open a project</strong><small>Continue project setup</small></span><ArrowRight size={15} /></button>
                <button onClick={() => navigate("/app")}><MessageSquare size={16} /><span><strong>Open project chat</strong><small>Search documents and context</small></span><ArrowRight size={15} /></button>
                <button onClick={() => navigate("/projects")}><CalendarDays size={16} /><span><strong>Review milestones</strong><small>Open project milestones</small></span><ArrowRight size={15} /></button>
              </div>
            </section>

            <section className="overview-panel recent-projects">
              <header>
                <div><p>Projects</p><h2>Recent workspaces</h2></div>
                <button onClick={() => navigate("/projects")}>View all <ArrowRight size={14} /></button>
              </header>
              {projects.length === 0 ? (
                <div className="overview-empty">
                  <FolderKanban size={24} />
                  <h3>No projects yet</h3>
                  <p>Create a project to start organising tasks and milestones.</p>
                  <button className="operations-primary" onClick={() => navigate("/projects")}>
                    <Plus size={16} /> Create project
                  </button>
                </div>
              ) : (
                <div className="recent-project-list">
                  {projects.slice(0, 6).map((project) => (
                    <button
                      key={project.id}
                      onClick={() => navigate(`/projects/${project.id}`)}
                    >
                      <span className="project-monogram">
                        {project.name.trim().slice(0, 2).toUpperCase()}
                      </span>
                      <span className="project-list-copy">
                        <strong>{project.name}</strong>
                        <small>{project.description || "No description"}</small>
                      </span>
                      <span className={`status status-${project.status}`}>{project.status}</span>
                      <ArrowRight size={15} />
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="overview-note">
              <ShieldCheck size={18} />
              <div>
                <strong>Agent activity is not yet connected</strong>
                <p>Pending approvals and agent-generated insights will appear here once those backend workflows are implemented.</p>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
