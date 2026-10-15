import Assistant from "./Assistant";
import { Facts, Source } from "./components";
import type { Citation, Scheme } from "./types";
export default function ScholarshipDetail({
  detail,
  schemeId,
}: {
  detail: { scholarship: Scheme; citation: Citation };
  schemeId: string;
}) {
  return (
    <section className="panel detail">
      <a href="#/scholarships" className="back">
        ← Back to scholarships
      </a>
      <div className="detail-heading">
        <span className="eyebrow">{detail.scholarship.provider}</span>
        <h2>{detail.scholarship.name}</h2>
        <p>{detail.scholarship.objective}</p>
      </div>
      <div className="detail-grid">
        <div>
          <h3>Target groups</h3>
          <Facts value={detail.scholarship.target_groups} />
          <h3>Eligibility criteria</h3>
          <Facts value={detail.scholarship.eligibility} />
          <h3>Benefits</h3>
          <Facts value={detail.scholarship.benefits} />
          <h3>Required documents</h3>
          <Facts value={detail.scholarship.documents_required} />
          <h3>Application procedure</h3>
          <Facts value={detail.scholarship.application} />
          <h3>Exclusions</h3>
          <Facts value={detail.scholarship.exclusions} />
          <h3>Selection and renewal</h3>
          <Facts value={detail.scholarship.selection} />
          {!!detail.scholarship.important_notes?.length && (
            <>
              <h3>Additional scheme notes</h3>
              <Facts value={detail.scholarship.important_notes} />
            </>
          )}
        </div>
        <aside>
          <div className="detail-aside">
            <h3>Understand your next step</h3>
            <p>
              Ask the assistant to explain these criteria or compare the
              available information. The scholarship authority makes the final
              eligibility decision.
            </p>
            <Source citation={detail.citation} />
          </div>
        </aside>
      </div>
      <Assistant schemeId={schemeId} />
    </section>
  );
}
