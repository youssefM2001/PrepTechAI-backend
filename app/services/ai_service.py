import httpx
import json
import re


def generate_first_question(formatted_cv, job_description_content, difficulty, type):


    job_description_content = job_description_content[:2000]

    prompt = f"""
You are a strict and experienced interviewer.

Candidate Profile:
{formatted_cv}

Job Description:
{job_description_content[:1000]}

Instructions:
- Ask ONE sharp and specific first question
- Focus on the MOST relevant experience for this job
- Avoid generic questions (e.g., "Tell me about yourself")
- Make the candidate explain something concrete (project, decision, challenge)
- Prefer "how", "why", or "what problem" questions
- Match difficulty: {difficulty}
- Interview type: {type}

Bad example:
- "Tell me about yourself"

Good examples:
- "How did you handle authentication in your Spring Boot project and why did you choose that approach?"
- "What was the most difficult issue you faced when working with data analysis and how did you solve it?"

Output ONLY the question.
"""


    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",  # or mistral:latest
                "prompt": prompt,
                "stream": False
            },
            timeout=60.0
        )

        data = response.json()

        return data["response"].strip()

    except Exception:
        return "Tell me about yourself."
    




def evaluate_answer(question: str, answer: str):

    prompt = f"""
You are a senior technical interviewer.

Evaluate this answer.

Question:
{question}

Answer:
{answer}

Your tasks:
1. Give concise feedback (max 2 lines)
2. Score from 0 to 10
3. Identify 2 strengths
4. Identify 2 weaknesses
5. Decide what topic should be explored next (1 short phrase)

Be strict and realistic.

Respond ONLY in valid JSON:

{{
  "feedback": "...",
  "score": 0,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "next_focus": "..."
}}
"""

    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200
                }
            },
            timeout=60.0
        )

        data = response.json()
        text = data["response"].strip()

        # 🔥 Robust JSON parsing
        try:
            result = json.loads(text)
        except Exception:
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                result = json.loads(match.group())
            else:
                raise ValueError("Invalid JSON from AI")

        # ✅ Safe extraction with defaults
        return {
            "feedback": result.get("feedback", "No feedback"),
            "score": result.get("score", 5),
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "next_focus": result.get("next_focus", "general improvement")
        }

    except Exception as e:
        print("❌ Evaluation error:", e)

        # ✅ fallback structure (VERY important)
        return {
            "feedback": "Unable to evaluate answer",
            "score": 5,
            "strengths": [],
            "weaknesses": [],
            "next_focus": "general"
        }



def generate_next_question(formatted_cv, job_description, history, result_data, difficulty, type):

    job_description = job_description[:1500]

    # 🧠 format history into readable conversation
    history_text = ""
    for msg in history:
        role = "Interviewer" if msg["role"] == "ai" else "Candidate"
        history_text += f"{role}: {msg['content']}\n"

    # 🔥 Extract last evaluation (CORE improvement)
    last_eval_text = ""
    answers = result_data.get("answers", [])

    if answers:
        last = answers[-1]

        last_eval_text = f"""
Last evaluation:
- Score: {last.get("score")}
- Strengths: {", ".join(last.get("strengths", []))}
- Weaknesses: {", ".join(last.get("weaknesses", []))}
- Next focus: {last.get("next_focus")}
"""

    prompt = f"""
You are a strict and intelligent interviewer conducting a {type} interview.

Candidate Profile:
{formatted_cv}

Job Description:
{job_description}

Conversation so far:
{history_text}

{last_eval_text}

Instructions:
- Ask ONE next question only
- Adapt based on the LAST evaluation

Behavior rules:
- If score < 5 → simplify and probe fundamentals
- If score 5-7 → ask clarification or real-world application
- If score > 7 → go deeper technically or ask edge cases
- If answer was vague → force specifics
- If answer was strong → challenge decisions and trade-offs
- Use "Next focus" topic if provided

Question quality:
- Must be specific to candidate context
- Must feel like a real interviewer follow-up
- Focus on reasoning, not definitions
- Avoid generic questions

Constraints:
- Do NOT repeat previous questions
- Match difficulty: {difficulty}
- Ask ONLY ONE question
- Do NOT explain anything

Output ONLY the question.
"""

    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 120
                }
            },
            timeout=60.0
        )

        data = response.json()
        return data["response"].strip()

    except Exception:
        return "Can you clarify your previous answer with more concrete details?"


def generate_final_report(result_json):

    answers = result_json.get("answers", [])

    # 🧠 format answers nicely
    formatted_answers = ""
    for i, item in enumerate(answers, 1):
        formatted_answers += f"""
Question {i}: {item['question']}
Answer: {item['answer']}
Feedback: {item['feedback']}
Score: {item['score']}/10
"""

    prompt = f"""
You are a senior interviewer.

Here is a full interview evaluation:

{formatted_answers}

Your task:
1. Give a final score (0–10)
2. List 2–3 strengths
3. List 2–3 weaknesses
4. Give an overall assessment (2–3 lines)
5. Give a hiring recommendation (YES or NO with reason)

Be critical and realistic.

Scoring guide:
- 0-4: Not qualified
- 5-6: Junior level, needs improvement
- 7-8: Good candidate
- 9-10: Strong hire

Respond ONLY in JSON:
{{
  "final_score": number,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "overall": "...",
  "hire_decision": "YES/NO",
  "reason": "..."
}}
"""


    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200
                }
            },
            timeout=60.0
        )

        data = response.json()
        text = data["response"].strip()

        # 🧠 Safe JSON extraction
        result = parse_json_safe(text)

        final_score = result.get("final_score", 5)
        strengths = result.get("strengths", ["Good effort"])
        weaknesses = result.get("weaknesses", ["Needs improvement"])

        return {
    "final_score": final_score,
    "strengths": strengths,
    "weaknesses": weaknesses,
    "overall": result.get("overall", ""),
    "hire_decision": result.get("hire_decision", "NO"),
    "reason": result.get("reason", "")
}


    except Exception:
        return {
    "final_score": 5,
    "strengths": ["Basic understanding shown"],
    "weaknesses": ["Evaluation incomplete due to parsing error"],
    "overall": "System could not fully evaluate performance.",
    "hire_decision": "NO",
    "reason": "Incomplete evaluation"
}








# EXTRACT STRUCTURED DATA USING AI
def extract_cv_data(cv_content: str):

    # Sanitize input: remove characters that break JSON generation
    cv_content = cv_content[:3000]
    cv_content = cv_content.replace('"', "'").replace('\\', '/')

    prompt = f"""You are an expert CV parser. Extract structured data from the CV below.

Return ONLY valid JSON, no explanation, no markdown, no code blocks.

Use this exact structure:
{{
  "education": [
    {{"degree": "...", "school": "...", "year": "..."}}
  ],
  "experience": [
    {{"title": "...", "company": "...", "duration": "...", "description": "..."}}
  ],
  "skills": ["...", "..."]
}}

Rules:
- Use empty lists [] if a section is missing
- Keep all string values short (under 100 chars)
- No trailing commas
- No newlines inside string values

CV:
{cv_content}

JSON:"""

    try:
        response = httpx.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,       # Lower = more deterministic
                    "num_predict": 800,    
                    "stop": ["```", "Note:"]  # Stop before extra commentary
                }
            },
            timeout=300.0
        )

        raw = response.json()["response"].strip()
        print("🔍 RAW AI RESPONSE:\n", raw[:500])  # Debug helper

        return parse_json_safe(raw)

    except Exception as e:
        print("❌ AI error:", e)
        return {"education": [], "experience": [], "skills": []}


# 🔥 NEW: Robust JSON parser
def parse_json_safe(text: str) -> dict:
    fallback = {"education": [], "experience": [], "skills": []}

    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code blocks if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 3. Extract first {...} block (handles leading/trailing text)
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        candidate = match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 4. Try to repair truncated JSON by closing open brackets
        try:
            repaired = repair_json(candidate)
            return json.loads(repaired)
        except Exception:
            pass

    print("⚠️ Could not parse JSON, returning fallback")
    return fallback


def repair_json(text: str) -> str:
    """Close any unclosed brackets/braces in truncated JSON."""
    # Remove trailing incomplete line
    lines = text.strip().splitlines()
    while lines and not lines[-1].strip().endswith(('}', ']', '"')):
        lines.pop()
    text = "\n".join(lines)

    # Count and close open brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')

    # Close in reverse order
    text = text.rstrip().rstrip(',')  # Remove trailing comma before closing
    text += ']' * open_brackets
    text += '}' * open_braces

    return text


# 🔥 3. FORMAT FOR AI (unchanged)
def format_cv_for_ai(data: dict):
    if not data:
        return "No data"

    text = ""

    skills = data.get("skills", [])
    if skills:
        text += "Skills:\n"
        text += ", ".join(skills) + "\n\n"

    experience = data.get("experience", [])
    if experience:
        text += "Experience:\n"
        for exp in experience:
            text += f"- {exp.get('title', '')} at {exp.get('company', '')} ({exp.get('duration', '')})\n"
            text += f"  {exp.get('description', '')}\n"
        text += "\n"

    education = data.get("education", [])
    if education:
        text += "Education:\n"
        for edu in education:
            text += f"- {edu.get('degree', '')}, {edu.get('school', '')} ({edu.get('year', '')})\n"

    return text


def prepare_cv_for_ai(cv_content: str):
    
    # 🔥 extract structured data
    data = extract_cv_data(cv_content)

    # 🔥 fallback if extraction fails
    if not data or not data.get("experience"):
        return cv_content[:1500]

    # 🔥 format clean CV
    return format_cv_for_ai(data)
