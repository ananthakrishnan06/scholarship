# Dataset integrity and provenance

The supplied scholarship data files are preserved. data/scholarship_dataset_ready.json is authoritative:
16 unique records; the metadata reports 18 initial source records and two exact
duplicates removed. The supplied data/combined_scholarship_schemes_cleaned.json also
contains 16 preserved records after deduplication. Original keys remain noncontiguous.

The loader validates counts, unique IDs, mandatory provenance and equality of every
original_record to its source-corpus counterpart. Ready JSONL is a supplied
id/text/metadata projection for retrieval, not a second authoritative record schema.
The application creates section chunks from the ready JSON to retain precise sources.
No semantic scholarships are merged and no source facts are added.

Known source issues: ST pre-matric income differs between Details and Eligibility;
the correct current income threshold requires official verification. Both disability schemes describe offline
implementation while specifying online application. These notes are preserved and
retrieved with the relevant sections and explained naturally in generated answers.

Many records lack source URLs/names. Empty URLs become null; the UI explicitly says
"Source information unavailable in dataset". No URLs are synthesized.
The corpus is a supplied snapshot. The application cannot verify live availability,
deadlines or current scholarship amounts without an updated authoritative source.

## Preserved files

| File under `data/` | Purpose and consumers |
|---|---|
| `scholarship_dataset_ready.json` | Authoritative 16-scheme dataset; backend corpus loader, section chunking, ingestion, API detail pages, tests and both evaluation modes. |
| `combined_scholarship_schemes_cleaned.json` | Source records; loaded at runtime to verify each ready record's original-record provenance. |
| `scholarship_dataset_ready.jsonl` | Supplied ID/text/metadata projection; retained as a useful data-stage artifact, not loaded by the section-based runtime. |
| `scholarship_dataset_QA_report.json` | Supplied QA summary; retained for dataset review. Its `dataset` field is the original basename, now relative to this directory. |

These are distinct representations, not duplicate files. Repository cleanup only
moved them; every file retains its original SHA-256. No records or facts changed.
See [the cleanup audit](REPOSITORY_CLEANUP.md).
