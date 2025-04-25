# AI prompt templates for the PDF Feedback System

# Prompt for analyzing chunks of long documents
LONG_CHUNK_ANALYSIS_PROMPT = """
You are an expert academic assessor. {requirements_context}

{chunk}

Extract key points, strengths, and weaknesses from this section.
"""

# Prompt for analyzing short documents directly
SHORT_DOCUMENT_ANALYSIS_PROMPT = """
You are an expert academic assessor. {requirements_context}

{assignment_text}

Provide a comprehensive assessment in the following JSON format:

```json
{{
    "title": "Assessment Title",
    "grade": "Letter grade (A+, A, A-, B+, etc.)",
    "score": A number between 0 and 100,
    "summary": "One paragraph summary of the work",
    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
    "detailed_feedback": "Comprehensive feedback in 3-4 paragraphs",
    "category_scores": {{
        "Content": Score between 0 and 100,
        "Structure": Score between 0 and 100,
        "Analysis": Score between 0 and 100,
        "Language": Score between 0 and 100,
        "References": Score between 0 and 100
    }}
}}
```

Ensure your assessment is fair, constructive, and specific to help the student improve.
"""

# Prompt for creating final assessment from combined summaries
FINAL_ASSESSMENT_PROMPT = """
You are an expert academic assessor. Below are summaries from different parts of a student assignment.

{combined_summary}

{requirements_context}

Provide the assessment in the following JSON format:

```json
{{
    "title": "Assessment Title",
    "grade": "Letter grade (A+, A, A-, B+, etc.)",
    "score": A number between 0 and 100,
    "summary": "One paragraph summary of the work",
    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
    "detailed_feedback": "Comprehensive feedback in 3-4 paragraphs",
    "category_scores": {{
        "Content": Score between 0 and 100,
        "Structure": Score between 0 and 100,
        "Analysis": Score between 0 and 100,
        "Language": Score between 0 and 100,
        "References": Score between 0 and 100
    }}
}}
```

Ensure your assessment is fair, constructive, and specific to help the student improve.
"""

# Prompt for analyzing documents via Gemini File API
FILE_API_ANALYSIS_PROMPT = """
You are an expert academic assessor. {requirements_context}

Provide a comprehensive assessment in the following JSON format:

```json
{{
    "title": "Assessment Title",
    "grade": "Letter grade (A+, A, A-, B+, etc.)",
    "score": A number between 0 and 100,
    "summary": "One paragraph summary of the work",
    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
    "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
    "detailed_feedback": "Comprehensive feedback in 3-4 paragraphs",
    "category_scores": {{
        "Content": Score between 0 and 100,
        "Structure": Score between 0 and 100,
        "Analysis": Score between 0 and 100,
        "Language": Score between 0 and 100,
        "References": Score between 0 and 100
    }}
}}
```

Ensure your assessment is fair, constructive, and specific to help the student improve.
"""