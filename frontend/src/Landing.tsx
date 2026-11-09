import { useEffect, useRef } from "react";
import "./Landing.css";
import { fluidSimulation } from "./fluidSimulation";

interface Props {
  onEnterApp: () => void;
  onLogin: () => void;
  onSignup: () => void;
}

const headingWords = ["Your", "documents,", "understood."];
const descriptionWords =
  "Ask questions across your PDFs and files, trace answers to relevant content, and search the web when you need more.".split(" ");

function FlowMark() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M2.5 9c2.5 0 2.5 4.2 5 4.2S10 9 12 9s2.5 4.2 5 4.2S19.5 9 21.5 9"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M2.5 15c2.5 0 2.5 4.2 5 4.2S10 15 12 15s2.5 4.2 5 4.2S19.5 15 21.5 15"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        opacity="0.5"
      />
    </svg>
  );
}

function ArrowUpRight() {
  return (
    <svg viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M3.5 12.5 12 4M5 4h7v7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Landing({ onEnterApp, onLogin, onSignup }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const root = rootRef.current;
    let revealFrame = 0;
    if (root) {
      revealFrame = requestAnimationFrame(() => root.classList.add("is-ready"));
    }
    const destroyFluid = canvas ? fluidSimulation(canvas) : () => undefined;

    return () => {
      cancelAnimationFrame(revealFrame);
      destroyFluid();
      root?.classList.remove("is-ready");
    };
  }, []);

  return (
    <main className="landing-root" ref={rootRef}>
      <section className="hero" id="top">
        <canvas ref={canvasRef} className="fluid-canvas" aria-hidden="true" />
        <div className="hero-scrim" aria-hidden="true" />

        <header className="nav">
          <a href="#top" className="brand" aria-label="Pagetrail home">
            <span className="brand-mark"><FlowMark /></span>
            <span>Pagetrail</span>
          </a>

          <div className="nav-links" aria-label="Pagetrail capabilities">
            <span>Document chat</span>
            <span>Web search</span>
            <span>Long-term memory</span>
          </div>

          <div className="nav-actions">
            <button type="button" className="nav-login" onClick={onLogin}>Log in</button>
            <button type="button" className="pill-button nav-cta" onClick={onSignup}>
              Get started <ArrowUpRight />
            </button>
          </div>
        </header>

        <div className="hero-content">
          <p className="hero-badge">
            <span className="badge-spark" aria-hidden="true" />
            Your files, connected
          </p>

          <h1 className="hero-title" aria-label="Your documents, understood.">
            {headingWords.map((word, index) => (
              <span
                className="reveal-word"
                key={word}
                aria-hidden="true"
                style={{ transitionDelay: (480 + index * 85) + "ms" }}
              >
                {word}{" "}
              </span>
            ))}
          </h1>

          <p className="hero-copy">
            {descriptionWords.map((word, index) => (
              <span
                className="reveal-word"
                key={index}
                style={{ transitionDelay: (1150 + index * 22) + "ms" }}
              >
                {word}{" "}
              </span>
            ))}
          </p>

          <div className="hero-actions">
            <button type="button" className="pill-button hero-primary" onClick={onEnterApp}>
              Start exploring <ArrowUpRight />
            </button>
            <button type="button" className="hero-secondary" onClick={onLogin}>
              I already have an account
            </button>
          </div>

          <div className="hero-formats" aria-label="Supported document formats">
            <span>PDF</span>
            <i />
            <span>DOCX</span>
            <i />
            <span>TXT</span>
            <i />
            <span>Markdown</span>
          </div>
        </div>

        <footer className="hero-footer">
          <span>© 2026 Pagetrail</span>
          <span>Document-aware AI, built for deeper research.</span>
        </footer>
      </section>
    </main>
  );
}
