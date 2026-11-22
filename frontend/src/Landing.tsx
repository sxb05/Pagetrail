import { useEffect, useRef, useState, type MouseEvent } from "react";
import "./Landing.css";
import GridScan from "./GridScan";
import brandLogoUrl from "./assets/pagetrail-icon.png";

interface Props {
  onEnterApp: () => void;
  onLogin: () => void;
  onSignup: () => void;
}

const headingWords = ["Your", "projects", "move", "forward."];

function ArrowUpRight() {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3.5 12.5 12 4M5 4h7v7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Landing({ onEnterApp, onLogin, onSignup }: Props) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [demoStep, setDemoStep] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeSection, setActiveSection] = useState("top");

  useEffect(() => {
    const root = rootRef.current;
    let revealFrame = 0;
    if (root) {
      revealFrame = requestAnimationFrame(() => root.classList.add("is-ready"));
    }
    return () => {
      cancelAnimationFrame(revealFrame);
      root?.classList.remove("is-ready");
    };
  }, []);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => {
      setDemoStep((current) => (current + 1) % 5);
    }, 2600);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const sections = ["top", "product", "features", "how-it-works", "workspace"]
      .map((id) => document.getElementById(id))
      .filter((section): section is HTMLElement => !!section);

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) setActiveSection(visible.target.id);
      },
      { rootMargin: "-18% 0px -58% 0px", threshold: [0.05, 0.25, 0.5] },
    );

    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  const scrollToSection = (event: MouseEvent<HTMLAnchorElement>, id: string) => {
    event.preventDefault();
    setMobileMenuOpen(false);
    setActiveSection(id);

    const section = document.getElementById(id);
    if (!section) return;

    window.history.pushState(null, "", `#${id}`);
    section.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
  };

  return (
    <main className="landing-root" ref={rootRef}>
      <section className="hero" id="top">
        <GridScan
          className="hero-grid-scan"
          cells={8}
          depth={3}
          scanDuration={2.4}
          scanDelay={1.6}
          clickEffect="ping"
        />
        <header className="nav">
          <a href="#top" className="brand" aria-label="Pagetrail home" onClick={(event) => scrollToSection(event, "top")}>
            <span className="brand-mark"><img src={brandLogoUrl} alt="" aria-hidden="true" /></span>
            <span>Pagetrail</span>
          </a>

          <nav className={`nav-links ${mobileMenuOpen ? "nav-links--open" : ""}`} aria-label="Primary navigation">
            <a className={activeSection === "product" ? "active" : ""} href="#product" onClick={(event) => scrollToSection(event, "product")}>Product</a>
            <a className={activeSection === "features" ? "active" : ""} href="#features" onClick={(event) => scrollToSection(event, "features")}>Features</a>
            <a className={activeSection === "how-it-works" ? "active" : ""} href="#how-it-works" onClick={(event) => scrollToSection(event, "how-it-works")}>How it works</a>
            <a className={activeSection === "workspace" ? "active" : ""} href="#workspace" onClick={(event) => scrollToSection(event, "workspace")}>Workspace</a>
          </nav>

          <div className="nav-actions">
            <button type="button" className="nav-login" onClick={onLogin}>Sign in</button>
            <button type="button" className="pill-button nav-cta" onClick={onSignup}>
              Start organising <ArrowUpRight />
            </button>
            <button
              type="button"
              className="nav-menu-button"
              aria-label={mobileMenuOpen ? "Close navigation" : "Open navigation"}
              aria-expanded={mobileMenuOpen}
              onClick={() => setMobileMenuOpen((current) => !current)}
            >
              <span /><span />
            </button>
          </div>
        </header>

        <div className="hero-content">
          <p className="hero-badge">
            <span className="badge-spark" aria-hidden="true" />
            AI project operations
          </p>

          <h1 className="hero-title" aria-label="Your projects move forward. Even when you're not watching.">
            {headingWords.map((word, index) => (
              <span
                className="reveal-word"
                key={word}
                aria-hidden="true"
                style={{ transitionDelay: (480 + index * 85) + "ms" }}
              >
                {word}
              </span>
            ))}
          </h1>

          <p className="hero-copy">
            Pagetrail turns project documents, team updates and scattered tasks into coordinated execution.
            Understand what is happening, identify what needs attention and move work forward with an
            AI-powered operations agent.
          </p>

          <div className="hero-actions">
            <button type="button" className="pill-button hero-primary" onClick={onEnterApp}>
              Start organising <ArrowUpRight />
            </button>
            <button type="button" className="hero-secondary" onClick={() => document.querySelector("#how-it-works")?.scrollIntoView({ behavior: "smooth" })}>
              Explore how it works
            </button>
          </div>
        </div>
      </section>

      <section className="landing-section product-section" id="product">
        <div className="section-heading">
          <p>Project intelligence</p>
          <h2>From scattered context to a clear next move.</h2>
        </div>
        <div className="demo-shell">
          <div className="demo-sidebar">
            <div className="demo-logo"><span><img src={brandLogoUrl} alt="" /></span>Pagetrail</div>
            {["Documents", "Context", "Actions", "Assignments", "Review"].map((label, index) => (
              <button
                type="button"
                key={label}
                className={demoStep === index ? "active" : ""}
                onClick={() => setDemoStep(index)}
              >
                <span>0{index + 1}</span>{label}
              </button>
            ))}
          </div>
          <div className="demo-workspace">
            <div className="demo-toolbar">
              <span>Launch operations</span>
              <span className="demo-status">Preview</span>
            </div>
            <div className="demo-content">
              <div className="demo-graph" aria-label="Project context preview">
                {["Brief", "Notes", "Tasks", "Milestones"].map((node, index) => (
                  <MotionNode key={node} label={node} index={index} />
                ))}
                <span className="demo-line line-one" />
                <span className="demo-line line-two" />
              </div>
              <div className="demo-insight">
                <p>Context understanding</p>
                <h3>{["Project brief indexed", "Meeting context connected", "Pending actions identified", "Owners can be suggested", "Actions await approval"][demoStep]}</h3>
                <div className="demo-progress"><span style={{ width: `${28 + demoStep * 16}%` }} /></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="landing-section features-section" id="features">
        <div className="section-heading">
          <p>One operational workspace</p>
          <h2>Coordinate work around what the project actually knows.</h2>
        </div>
        <div className="feature-grid">
          <article className="feature feature-wide">
            <span className="feature-index">01</span>
            <div><p>Project intelligence</p><h3>Understand every source of truth.</h3></div>
            <div className="feature-visual knowledge-visual"><span>Brief</span><span>Meeting</span><span>Tasks</span></div>
          </article>
          <article className="feature">
            <span className="feature-index">02</span>
            <p>Task coordination</p>
            <h3>Owners, priorities and dependencies stay connected.</h3>
            <div className="feature-visual task-visual"><i /><i /><i /></div>
          </article>
          <article className="feature">
            <span className="feature-index">03</span>
            <p>Project monitoring</p>
            <h3>See blockers and overdue work early.</h3>
            <div className="feature-visual monitor-visual"><span /><span /><span /></div>
          </article>
          <article className="feature feature-wide">
            <span className="feature-index">04</span>
            <div><p>Human-controlled execution</p><h3>Review meaningful actions before they run.</h3></div>
            <div className="approval-visual"><span>Approve action</span><button type="button">Review</button></div>
          </article>
        </div>
      </section>

      <section className="landing-section process-section" id="how-it-works">
        <div className="section-heading">
          <p>How it works</p>
          <h2>A traceable path from knowledge to execution.</h2>
        </div>
        <ol className="process-list">
          {[
            ["Project knowledge", "Documents and meeting notes"],
            ["Context understanding", "Relevant project context"],
            ["Action planning", "Tasks and dependencies"],
            ["Human approval", "Operator review"],
            ["Coordinated execution", "Controlled operations"],
            ["Verified results", "Clear audit trail"],
          ].map(([title, detail], index) => (
            <li key={title}>
              <span>0{index + 1}</span>
              <strong>{title}</strong>
              <small>{detail}</small>
            </li>
          ))}
        </ol>
      </section>

      <section className="landing-section workspace-section" id="workspace">
        <div className="workspace-copy">
          <p>Built for the work itself</p>
          <h2>One calm place for projects, tasks and evidence.</h2>
          <button type="button" className="pill-button" onClick={onEnterApp}>Open workspace <ArrowUpRight /></button>
        </div>
        <div className="workspace-preview">
          <div className="preview-chrome"><span /><span /><span /></div>
          <div className="preview-body">
            <aside><b>Pagetrail</b><span>Overview</span><span className="active">Tasks</span><span>Milestones</span><span>Knowledge</span></aside>
            <div className="preview-main">
              <div className="preview-header"><span>Website launch</span><button type="button">New task</button></div>
              {["Finalize release plan", "Review accessibility", "Publish launch brief"].map((task, index) => (
                <div className="preview-task" key={task}><span>{String(index + 1).padStart(2, "0")}</span><strong>{task}</strong><small>{["In progress", "Blocked", "To do"][index]}</small></div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="landing-final">
        <p>Ready to organise what is next?</p>
        <h2>Turn project knowledge into coordinated action.</h2>
        <button type="button" className="pill-button" onClick={onSignup}>Create your workspace <ArrowUpRight /></button>
      </section>

      <footer className="landing-footer">
        <a href="#top" className="brand" onClick={(event) => scrollToSection(event, "top")}><span className="brand-mark"><img src={brandLogoUrl} alt="" /></span><span>Pagetrail</span></a>
        <nav aria-label="Footer navigation"><a href="#product" onClick={(event) => scrollToSection(event, "product")}>Product</a><a href="#features" onClick={(event) => scrollToSection(event, "features")}>Features</a><a href="#how-it-works" onClick={(event) => scrollToSection(event, "how-it-works")}>How it works</a></nav>
        <span>© 2026 Pagetrail</span>
      </footer>
    </main>
  );
}

function MotionNode({ label, index }: { label: string; index: number }) {
  return <span className={`demo-node demo-node-${index + 1}`}><i />{label}</span>;
}
