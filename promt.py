prompt = """Analyze this resume for ATS optimization and grammar:
{resume_text}
---
Return JSON with:
- score (1-10)
- grammar_errors (list)
- missing_keywords (list)
- improved_bullets (list of rewritten weak bullet points)"""