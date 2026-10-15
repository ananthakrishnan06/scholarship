import type { ReactNode } from "react";
import { navigate } from "./navigation";

export default function Workspace({
  route,
  title,
  children,
}: {
  route: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#/">
          <span className="brand-icon">🎓</span>
          <span>
            Scholarship<span className="brand-sub">NAVIGATOR</span>
          </span>
        </a>
        <div className="workspace-label">STUDENT WORKSPACE</div>
        <nav aria-label="Main navigation">
          {[
            ["/", "◫", "Overview"],
            ["/scholarships", "▤", "Scholarships"],
            ["/assistant", "✦", "AI assistant"],
          ].map(([path, icon, label]) => (
            <a
              key={path}
              className={
                (path === "/" ? route === "/" : route.startsWith(path))
                  ? "active"
                  : ""
              }
              href={"#" + path}
            >
              <span aria-hidden="true">{icon}</span>
              {label}
              {label === "AI assistant" && <small>ASK</small>}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span>✓</span>
          <strong>Clarity, with evidence.</strong>
          <p>Ask a question. Explore the sources. Take your next step.</p>
        </div>
        <div className="sidebar-footer">
          <span className="avatar">SN</span>
          <div>
            <strong>Student Workspace</strong>
            <small>Offline RAG Grounded</small>
          </div>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <span>Scholarship Eligibility Navigator</span>
          <span className="data-label">
            <i /> 16 Official Schemes • Grounded
          </span>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <span className="eyebrow">
                A LITTLE GUIDANCE. MORE POSSIBILITY.
              </span>
              <h1>{title}</h1>
              <p>
                Find support for your education, with the information you need
                to move forward.
              </p>
            </div>
            {route !== "/assistant" && (
              <button
                className="button primary"
                onClick={() => navigate("/assistant")}
              >
                Ask the AI assistant ↗
              </button>
            )}
          </div>
          {children}
          <footer className="page-footer">
            <span>Scholarship Navigator</span>
            <span>Scholarship guidance, grounded in authentic sources.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
