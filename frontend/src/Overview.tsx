import { useEffect, useState, type FormEvent } from "react";
import {
  ArrowRight,
  CalendarDays,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FolderKanban,
  LayoutList,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Plus,
  Search,
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

type PendingTask = {
  id: number;
  project_id: number;
  project_name?: string | null;
  title: string;
  status: string;
  priority: string;
  due_date?: string | null;
};

type UpcomingMilestone = {
  id: number;
  project_id: number;
  project_name?: string | null;
  title: string;
  status: string;
  due_date?: string | null;
};

type RecentActivity = {
  type: "project" | "task" | "milestone";
  title: string;
  detail: string;
  occurred_at?: string | null;
  project_id: number;
};

type OverviewDetails = {
  pending_tasks: PendingTask[];
  upcoming_milestones: UpcomingMilestone[];
  recent_activity: RecentActivity[];
  pending_approvals: Array<{ id: number; action_type: string; requested_at: string }>;
  agent_insights: string[];
};

type Props = {
  authenticatedFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
  navigate: (path: string) => void;
  username: string;
  onLogout: () => void;
};

export default function Overview({ authenticatedFetch, navigate, username, onLogout }: Props) {
  const [metrics, setMetrics] = useState<Metrics>({
    active_projects: 0,
    total_tasks: 0,
    completed_tasks: 0,
    overdue_tasks: 0,
    blocked_tasks: 0,
  });
  const [projects, setProjects] = useState<Project[]>([]);
  const [details, setDetails] = useState<OverviewDetails>({
    pending_tasks: [],
    upcoming_milestones: [],
    recent_activity: [],
    pending_approvals: [],
    agent_insights: [],
  });
  const [askText, setAskText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const [metricsResponse, projectsResponse, detailsResponse] = await Promise.all([
          authenticatedFetch("/api/projects/overview/metrics"),
          authenticatedFetch("/api/projects"),
          authenticatedFetch("/api/projects/overview/details"),
        ]);
        if (!metricsResponse.ok || !projectsResponse.ok || !detailsResponse.ok) {
          throw new Error("Unable to load operations overview.");
        }
        setMetrics(await metricsResponse.json());
        setProjects(await projectsResponse.json());
        setDetails(await detailsResponse.json());
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

  const askPagetrail = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const prompt = askText.trim();
    if (!prompt) return;
    navigate(`/app?prompt=${encodeURIComponent(prompt)}`);
  };

  return (
    <main className="operations-shell overview-shell">
      <aside className="overview-sidebar">
        <button className="overview-brand" onClick={() => navigate("/")} aria-label="Pagetrail overview">
          <span className="overview-brand-mark">P</span>
          <strong>Pagetrail</strong>
        </button>
        <nav className="overview-navigation" aria-label="Workspace navigation">
          <button className="active" onClick={() => navigate("/overview")}><LayoutDashboard size={16} /> Overview</button>
          <button onClick={() => navigate("/projects")}><FolderKanban size={16} /> Projects</button>
          <button onClick={() => navigate("/app")}><MessageSquare size={16} /> AI Assistant</button>
          <button className="overview-signout-mobile" onClick={onLogout}><LogOut size={16} /> Sign out</button>
        </nav>
        <div className="overview-user">
          <span>{username.slice(0, 1).toUpperCase()}</span>
          <small>{username}</small>
          <button type="button" onClick={onLogout} aria-label="Sign out" title="Sign out"><LogOut size={16} /></button>
        </div>
      </aside>

      <div className="overview-main">
        <header className="operations-topbar overview-topbar">
          <span>Overview</span>
          <button className="operations-back" onClick={() => navigate("/app")}>
            <MessageSquare size={16} /> AI Assistant
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

        <form className="overview-ask" onSubmit={askPagetrail}>
          <Search size={18} aria-hidden="true" />
          <input
            value={askText}
            onChange={(event) => setAskText(event.target.value)}
            placeholder="Ask Pagetrail about a project, task or milestone"
            aria-label="Ask Pagetrail"
          />
          <button type="submit" disabled={!askText.trim()}>
            Ask <ArrowRight size={15} />
          </button>
        </form>

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

            <section className="overview-grid overview-detail-grid">
              <div className="overview-panel">
                <header>
                  <div><p>Work queue</p><h2>Pending tasks</h2></div>
                  <Clock3 size={17} />
                </header>
                {details.pending_tasks.length === 0 ? (
                  <div className="overview-empty compact"><CheckCircle2 size={20} /><h3>No pending tasks</h3><p>All visible project tasks are completed.</p></div>
                ) : (
                  <div className="overview-list">
                    {details.pending_tasks.map((task) => (
                      <button key={task.id} onClick={() => navigate(`/projects/${task.project_id}`)}>
                        <span><strong>{task.title}</strong><small>{task.project_name || `Project ${task.project_id}`}</small></span>
                        <span className={`status status-${task.status}`}>{task.status.replace("_", " ")}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="overview-panel">
                <header>
                  <div><p>Schedule</p><h2>Upcoming milestones</h2></div>
                  <CalendarDays size={17} />
                </header>
                {details.upcoming_milestones.length === 0 ? (
                  <div className="overview-empty compact"><CalendarDays size={20} /><h3>No upcoming milestones</h3><p>Add milestones to a project to see them here.</p></div>
                ) : (
                  <div className="overview-list">
                    {details.upcoming_milestones.map((milestone) => (
                      <button key={milestone.id} onClick={() => navigate(`/projects/${milestone.project_id}`)}>
                        <span><strong>{milestone.title}</strong><small>{milestone.project_name || `Project ${milestone.project_id}`}</small></span>
                        <small>{milestone.due_date ? new Date(milestone.due_date).toLocaleDateString() : "No date"}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="overview-grid overview-detail-grid">
              <div className="overview-panel">
                <header>
                  <div><p>Recent activity</p><h2>Latest changes</h2></div>
                </header>
                {details.recent_activity.length === 0 ? (
                  <div className="overview-empty compact"><Clock3 size={20} /><h3>No recent activity</h3><p>Project updates will appear here.</p></div>
                ) : (
                  <div className="overview-list">
                    {details.recent_activity.map((activity, index) => (
                      <button key={`${activity.type}-${activity.project_id}-${index}`} onClick={() => navigate(`/projects/${activity.project_id}`)}>
                        <span><strong>{activity.title}</strong><small>{activity.detail}</small></span>
                        <small>{activity.occurred_at ? new Date(activity.occurred_at).toLocaleDateString() : ""}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="overview-panel">
                <header>
                  <div><p>Agent</p><h2>Insights and approvals</h2></div>
                  <ShieldCheck size={17} />
                </header>
                {details.agent_insights.length === 0 && details.pending_approvals.length === 0 ? (
                  <div className="overview-empty compact"><ShieldCheck size={20} /><h3>No agent activity</h3><p>Agent insights and pending approvals will appear here when available.</p></div>
                ) : (
                  <div className="overview-list">
                    {details.pending_approvals.map((approval) => (
                      <button key={approval.id} onClick={() => navigate("/projects")}>
                        <span><strong>{approval.action_type}</strong><small>Pending approval</small></span>
                        <small>{new Date(approval.requested_at).toLocaleDateString()}</small>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </section>
          </>
        )}
        </div>
      </div>
    </main>
  );
}
