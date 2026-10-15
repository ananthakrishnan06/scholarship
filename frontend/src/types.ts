export type Citation = {
  scheme_id: string;
  scheme_name: string;
  source_name: string | null;
  source_url: string | null;
  retrieved_from: string;
  original_record_key?: string;
  excerpt?: string | null;
};
export type Scheme = {
  scheme_id: string;
  name: string;
  provider: string;
  objective?: string;
  benefits: unknown;
  eligibility: unknown;
  documents_required: unknown;
  application: unknown;
  important_notes: string[];
  target_groups?: unknown;
  tags?: unknown;
  exclusions?: unknown;
  selection?: unknown;
  citation?: Citation;
};
export type Answer = {
  answer: string;
  sources: Citation[];
  status: "success" | "out_of_scope" | "insufficient_evidence" | "error";
  error?: { code: string; message: string } | null;
};
