import type { Scheme } from "./types";
import { navigate } from "./navigation";
export default function Dashboard({ schemes }: { schemes: Scheme[] }) {
  return (
    <>
      <section className="hero">
        <div>
          <span className="eyebrow">MAKE YOUR NEXT MOVE</span>
          <h2>
            More opportunities.
            <br />
            Less guesswork.
          </h2>
          <p>
            Ask about scholarships in your own words. Explore eligibility
            criteria, benefits, documents, and how to apply.
          </p>
          <button
            className="button light"
            onClick={() => navigate("/assistant")}
          >
            Ask about scholarships <span>→</span>
          </button>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orb" />
          <div className="book">
            <span>
              YOUR
              <br />
              NEXT
              <br />
              CHAPTER
            </span>
            <i>↗</i>
          </div>
          <span className="floating-tag">✦ A path worth exploring</span>
        </div>
      </section>
      <section className="stats" aria-label="Workspace summary">
        <div>
          <span className="stat-icon">▤</span>
          <strong>{schemes.length}</strong>
          <span>Scholarships in the dataset</span>
        </div>
        <div>
          <span className="stat-icon">✦</span>
          <strong>AI</strong>
          <span>Ask in your own words</span>
        </div>
        <div>
          <span className="stat-icon">✓</span>
          <strong>Sources</strong>
          <span>Supporting scholarship information</span>
        </div>
      </section>
      <div className="section-heading">
        <div>
          <h2>Start exploring</h2>
          <p>A few possibilities from the scholarship dataset.</p>
        </div>
        <a href="#/scholarships">View all scholarships →</a>
      </div>
    </>
  );
}
