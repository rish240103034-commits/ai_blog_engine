"""
AI Blog Engine - Multi-Agent Blog Generation System
Backend: Flask + Groq API (FREE — 14,400 req/day, ~1s response)
Get your free key at: https://console.groq.com
"""

import os
import json
import re
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


def call_groq(prompt: str, max_tokens: int = 4096) -> str:
    """
    Call Groq API using the requests library.
    Raises a clear error message on any failure.
    """
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set. "
            "Get free key at https://console.groq.com "
            "then add to Render > Environment > GROQ_API_KEY"
        )

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "messages":    [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens":  max_tokens,
    }

    try:
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=25)
    except requests.exceptions.Timeout:
        raise RuntimeError("Groq API timed out. Try again.")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Cannot reach Groq API. Check network.")

    if resp.status_code == 401:
        raise RuntimeError(
            "Groq API key is invalid (401 Unauthorized). "
            "Go to https://console.groq.com/keys, create a new key, "
            "and update GROQ_API_KEY in Render > Environment."
        )
    if resp.status_code == 403:
        raise RuntimeError(
            "Groq API key is forbidden (403). "
            "Your key may be invalid or your Groq account needs verification. "
            "Go to https://console.groq.com/keys and create a fresh key."
        )
    if resp.status_code == 429:
        raise RuntimeError(
            "Groq rate limit hit (429). Wait 1 minute and try again. "
            "Free tier: 30 requests/minute."
        )
    if not resp.ok:
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:200]}")

    try:
        return resp.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Groq response format: {resp.text[:200]}")


def parse_json_safe(raw: str, fallback: dict) -> dict:
    """Strip markdown fences and parse JSON, return fallback on failure."""
    cleaned = re.sub(r"```json\s*|```\s*", "", raw).strip()
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return fallback


# ─────────────────────────────────────────────
# AGENT 1 — Research (Intent + Keywords + SERP)
# ─────────────────────────────────────────────
def agent_research(keyword: str) -> dict:
    prompt = f"""You are an SEO research expert. Analyze the keyword: "{keyword}"

Respond with ONLY a valid JSON object. No explanation, no markdown fences, just raw JSON:

{{
  "intent": {{
    "intent_type": "informational",
    "confidence": "high",
    "reasoning": "explain in one sentence",
    "user_goal": "what the user wants",
    "content_type": "type of content e.g. how-to guide"
  }},
  "keywords": {{
    "primary_keyword": "{keyword}",
    "secondary_keywords": ["term1", "term2", "term3", "term4", "term5"],
    "long_tail_keywords": ["long phrase 1", "long phrase 2", "long phrase 3"],
    "lsi_keywords": ["related1", "related2", "related3"],
    "question_keywords": ["What is {keyword}?", "How to use {keyword}?", "Why does {keyword} matter?"],
    "search_volume_estimate": "medium",
    "competition_level": "medium"
  }},
  "serp_gaps": {{
    "common_topics_covered": ["topic1", "topic2", "topic3"],
    "content_gaps": ["gap1", "gap2", "gap3"],
    "unique_angles": ["angle1", "angle2"],
    "competitor_weaknesses": ["weakness1", "weakness2"],
    "our_opportunity": "one sentence opportunity",
    "recommended_word_count": 1500
  }}
}}"""

    raw = call_groq(prompt, max_tokens=1500)
    return parse_json_safe(raw, {
        "intent": {
            "intent_type": "informational", "confidence": "medium",
            "reasoning": "General informational topic",
            "user_goal": "Learn about the topic",
            "content_type": "Educational guide"
        },
        "keywords": {
            "primary_keyword": keyword,
            "secondary_keywords": [f"{keyword} guide", f"{keyword} tips",
                                   f"best {keyword}", f"{keyword} tutorial",
                                   f"{keyword} for beginners"],
            "long_tail_keywords": [f"how to {keyword}", f"best {keyword} for beginners",
                                   f"{keyword} step by step guide"],
            "lsi_keywords": [f"{keyword} strategy", f"{keyword} techniques", f"{keyword} methods"],
            "question_keywords": [f"What is {keyword}?", f"How does {keyword} work?",
                                  f"Why is {keyword} important?"],
            "search_volume_estimate": "medium",
            "competition_level": "medium"
        },
        "serp_gaps": {
            "common_topics_covered": ["Basic overview", "Common use cases", "Getting started"],
            "content_gaps": ["In-depth practical examples", "Expert tips", "Common mistakes"],
            "unique_angles": ["Step-by-step walkthrough", "Real-world case studies"],
            "competitor_weaknesses": ["Lack of examples", "Outdated information"],
            "our_opportunity": f"Most practical and complete guide on {keyword}",
            "recommended_word_count": 1500
        }
    })


# ─────────────────────────────────────────────
# AGENT 2 — Outline Generator
# ─────────────────────────────────────────────
def agent_outline(keyword: str, research: dict) -> dict:
    kws  = research.get("keywords", {})
    gaps = research.get("serp_gaps", {})
    sec  = ", ".join(kws.get("secondary_keywords", [])[:3])
    gap  = "; ".join(gaps.get("content_gaps", [])[:3])

    prompt = f"""Create an SEO blog outline for the keyword: "{keyword}"
Secondary keywords: {sec}
Content gaps to address: {gap}

Return ONLY raw JSON (no markdown, no explanation):
{{
  "h1_title": "Compelling title with '{keyword}'",
  "meta_description": "155 char meta description mentioning '{keyword}'",
  "intro_hook": "One sentence opening hook description",
  "sections": [
    {{"h2": "Section 1", "purpose": "covers X", "h3_subsections": ["Sub A", "Sub B"]}},
    {{"h2": "Section 2", "purpose": "covers Y", "h3_subsections": ["Sub A", "Sub B"]}},
    {{"h2": "Section 3", "purpose": "covers Z", "h3_subsections": ["Sub A"]}},
    {{"h2": "Section 4", "purpose": "covers W", "h3_subsections": ["Sub A", "Sub B"]}},
    {{"h2": "Section 5", "purpose": "covers V", "h3_subsections": ["Sub A"]}}
  ],
  "conclusion_summary": "what conclusion covers",
  "estimated_read_time": "7 min read",
  "target_word_count": 1400
}}"""

    raw = call_groq(prompt, max_tokens=1000)
    return parse_json_safe(raw, {
        "h1_title": f"The Complete Guide to {keyword}: Expert Tips & Strategies",
        "meta_description": (
            f"Learn everything about {keyword} with expert tips, "
            f"practical examples and step-by-step strategies."
        ),
        "intro_hook": f"Why {keyword} matters more than ever",
        "sections": [
            {"h2": f"What Is {keyword}?", "purpose": "Definition",
             "h3_subsections": ["Definition", "Why it matters"]},
            {"h2": f"How {keyword} Works", "purpose": "Mechanics",
             "h3_subsections": ["Core process", "Key components"]},
            {"h2": f"Top Benefits of {keyword}", "purpose": "Benefits",
             "h3_subsections": ["Benefit 1", "Benefit 2"]},
            {"h2": f"How to Get Started with {keyword}", "purpose": "Practical steps",
             "h3_subsections": ["Step 1", "Step 2", "Step 3"]},
            {"h2": f"Common {keyword} Mistakes to Avoid", "purpose": "Pitfalls",
             "h3_subsections": ["Mistake 1", "Mistake 2"]},
        ],
        "conclusion_summary": "Recap and call to action",
        "estimated_read_time": "7 min read",
        "target_word_count": 1400
    })


# ─────────────────────────────────────────────
# AGENT 3 — Blog Writer (plain markdown, no JSON)
# ─────────────────────────────────────────────
def agent_write_blog(keyword: str, outline: dict, keywords: dict) -> str:
    sections_text = ""
    for s in outline.get("sections", []):
        sections_text += f"\n## {s.get('h2', '')}\n"
        for h3 in s.get("h3_subsections", []):
            sections_text += f"### {h3}\n"

    secondary = ", ".join(keywords.get("secondary_keywords", [])[:4])
    long_tail  = ", ".join(keywords.get("long_tail_keywords", [])[:2])

    prompt = f"""Write a complete, high-quality SEO blog post in markdown.

Title: {outline.get("h1_title", keyword)}
Primary keyword: "{keyword}"
Secondary keywords (use naturally): {secondary}
Long-tail keywords (include where natural): {long_tail}

Use this exact heading structure:
{sections_text}

Rules:
- Write 1300-1600 words
- Start with a 2-3 sentence intro paragraph (no heading before it)
- Use ## for H2 and ### for H3 exactly as shown above
- Use "{keyword}" naturally every 150-200 words
- Expert, friendly, conversational tone
- Include practical examples and actionable tips in every section
- End with a strong call-to-action conclusion paragraph
- NEVER use: "delve", "in today's fast-paced world", "it's worth noting",
  "leverage", "In conclusion", "To summarize", "As we've seen"
- Use contractions freely: you'll, it's, don't, we're, isn't

Write the full blog post now:"""

    return call_groq(prompt, max_tokens=4096)


# ─────────────────────────────────────────────
# AGENT 4 — Humanizer
# ─────────────────────────────────────────────
def agent_humanize(blog: str, keyword: str) -> str:
    if len(blog.split()) < 200:
        return blog

    prompt = f"""Polish this blog post to sound more natural and human.
Keep ALL ## and ### markdown headings exactly as written.
Keep the keyword "{keyword}" throughout.

Improvements to make:
- Use contractions (it's, you'll, don't, they're)
- Vary sentence lengths — mix short punchy ones with longer detailed ones
- Add 1-2 genuine rhetorical questions to engage the reader
- Remove any remaining robotic phrases
- Maintain 1300-1600 words
- Keep all ## and ### headings unchanged

Blog:
---
{blog[:5500]}
---

Write the polished version in markdown (blog text only, no explanation):"""

    result = call_groq(prompt, max_tokens=4096)
    return result if result and len(result.split()) > 200 else blog


# ─────────────────────────────────────────────
# SEO SCORER (pure Python — no API call)
# ─────────────────────────────────────────────
def seo_score(keyword: str, blog: str, outline: dict) -> dict:
    wc       = len(blog.split())
    kw_count = blog.lower().count(keyword.lower())
    density  = round((kw_count / max(wc, 1)) * 100, 2)
    has_h2   = "## " in blog
    has_h3   = "### " in blog
    meta     = outline.get("meta_description", "")
    meta_len = len(meta)
    title    = outline.get("h1_title", "")
    score    = 0
    recs     = []

    if wc >= 1200:   score += 20
    elif wc >= 800:  score += 12; recs.append("Increase word count above 1200.")
    else:            score += 5;  recs.append("Content too short — aim for 1200+ words.")

    if 0.5 <= density <= 2.5:  score += 20
    elif density < 0.5:        score += 8;  recs.append(f"Low keyword density ({density}%). Use '{keyword}' more naturally.")
    else:                      score += 8;  recs.append(f"High density ({density}%). Reduce keyword repetition.")

    if has_h2 and has_h3:  score += 20
    elif has_h2:           score += 12; recs.append("Add ### H3 subheadings for better structure.")
    else:                  recs.append("Add ## H2 and ### H3 headings.")

    if 140 <= meta_len <= 160:   score += 20
    elif 100 <= meta_len < 140:  score += 12; recs.append("Meta description slightly short (aim 150-160 chars).")
    elif meta_len > 160:         score += 10; recs.append("Meta description too long — trim to 160 chars.")
    else:                        score += 5;  recs.append("Add a proper meta description.")

    if keyword.lower() in title.lower(): score += 10
    else:                                recs.append("Include the keyword in the H1 title.")

    if wc > 0 and kw_count > 0: score += 10

    return {
        "seo_score": min(score, 100),
        "word_count": wc,
        "keyword_count": kw_count,
        "keyword_density": density,
        "has_proper_headings": has_h2 and has_h3,
        "meta_description_length": meta_len,
        "recommendations": recs if recs else ["Excellent! Content is well-optimized."],
        "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"
    }


# ─────────────────────────────────────────────
# MAIN ENDPOINT
# ─────────────────────────────────────────────
@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    if not data or "keyword" not in data:
        return jsonify({"error": "Missing 'keyword' in request body"}), 400

    keyword = data["keyword"].strip()
    if not keyword:
        return jsonify({"error": "Keyword cannot be empty"}), 400
    if len(keyword) > 200:
        return jsonify({"error": "Keyword too long (max 200 chars)"}), 400
    if not GROQ_API_KEY:
        return jsonify({"error":
            "GROQ_API_KEY not set. Get free key at https://console.groq.com "
            "then add to Render > Environment > GROQ_API_KEY"}), 500

    try:
        print(f"[1/4] Research — {keyword}")
        research   = agent_research(keyword)

        print("[2/4] Outline")
        outline    = agent_outline(keyword, research)

        print("[3/4] Writing blog")
        raw_blog   = agent_write_blog(keyword, outline, research.get("keywords", {}))

        print("[4/4] Humanizing")
        final_blog = agent_humanize(raw_blog, keyword)
        if not final_blog or len(final_blog.split()) < 100:
            final_blog = raw_blog

        final_seo = seo_score(keyword, final_blog, outline)
        print(f"[DONE] {final_seo['word_count']} words | SEO: {final_seo['seo_score']}/100")

        return jsonify({
            "success":    True,
            "keyword":    keyword,
            "intent":     research.get("intent", {}),
            "keywords":   research.get("keywords", {}),
            "serp_gaps":  research.get("serp_gaps", {}),
            "outline":    outline,
            "seo_report": final_seo,
            "final_blog": final_blog
        })

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    print("=" * 50)
    print("  AI Blog Engine — Multi-Agent System")
    print("  Running at http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
