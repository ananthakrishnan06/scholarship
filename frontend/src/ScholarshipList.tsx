import { schemeHref } from "./navigation";
import type { Scheme } from "./types";

type Props = {
  route: string;
  schemes: Scheme[];
  search: string;
  setSearch: (v: string) => void;
  busy: boolean;
  error: string;
  discover: (event: React.FormEvent) => Promise<void>;
};

const POPULAR_TAGS = ["All", "OBC", "Girls", "SC / ST", "Engineering", "Merit-cum-Means"];

export default function ScholarshipList({
  route,
  schemes,
  search,
  setSearch,
  busy,
  error,
  discover,
}: Props) {
  return (
    <>
      {route === "/scholarships" && (
        <div className="search-section">
          <div className="search-row">
            <form onSubmit={discover}>
              <label className="sr-only" htmlFor="search">
                Search scholarships
              </label>
              <input
                id="search"
                placeholder="Search by scholarship name, category, or keyword (e.g. OBC, Pragati)…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button className="button primary" disabled={busy}>
                {busy ? "Searching…" : "Search"}
              </button>
            </form>
          </div>
          <div className="filter-chips">
            {POPULAR_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                className={
                  "chip " +
                  (search === tag || (tag === "All" && !search) ? "active" : "")
                }
                onClick={() => {
                  const val = tag === "All" ? "" : tag;
                  setSearch(val);
                }}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>
      )}
      <div className="cards">
        {(route === "/" ? schemes.slice(0, 4) : schemes).map((s) => (
          <article className="scholar-card" key={s.scheme_id}>
            <div className="card-top">
              <span className="scheme-icon">🎓</span>
              <span className="badge explore">VERIFIED SCHEME</span>
            </div>
            <span className="provider">{s.provider}</span>
            <h3>{s.name}</h3>
            <p>
              {s.objective ||
                "Explore official benefits, required documents, and verified eligibility criteria."}
            </p>
            <div className="card-footer">
              <span>Official Record</span>
              <a href={schemeHref(s.scheme_id)}>View details ↗</a>
            </div>
          </article>
        ))}
      </div>
      {!schemes.length && !busy && !error && (
        <div className="panel empty">
          No scholarships found matching your search. Try another keyword.
        </div>
      )}
    </>
  );
}
