# Scholarship Eligibility Engine

This is the next layer after `scholarship_dataset_ready.json`.

## Architecture

Student profile
→ deterministic eligibility engine
→ eligible / needs_verification / not_eligible
→ RAG retrieval
→ LLM explanation

## Important rule

The engine is deliberately conservative:

- `eligible`: all mapped rules passed and required fields were supplied.
- `not_eligible`: at least one mapped hard rule failed.
- `needs_verification`: no mapped hard rule failed, but information is missing or an institution/merit condition still requires verification.

The engine does **not** guess missing information.

## Files

- `eligibility_engine.py` — matching logic
- `student_profile_schema.json` — profile fields
- `README.md` — architecture and usage

## Example

```python
import json
from eligibility_engine import explainable_matches

with open("scholarship_dataset_ready.json", encoding="utf-8") as f:
    dataset = json.load(f)

profile = {
    "age": 19,
    "state": "Kerala",
    "category": "OBC",
    "annual_family_income": 250000,
    "course_level": "undergraduate",
    "course_type": "professional",
    "year_of_study": 3,
    "study_mode": "regular",
    "gender": "male",
    "disability_percentage": 0,
    "receiving_other_scholarship": False
}

result = explainable_matches(profile, dataset)
```

## Do not let the LLM decide eligibility

Use the LLM after this engine. The LLM should receive the matched scheme records and explain:
1. why the student matches,
2. which conditions are still unverified,
3. what documents are required,
4. what the source says.

It should never invent a missing threshold or eligibility condition.
