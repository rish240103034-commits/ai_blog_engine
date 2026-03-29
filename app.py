"""
AI Blog Engine - Multi-Agent Blog Generation System
Backend: Flask + Groq API (FREE — 14,400 req/day, ~1s response)
Get your free key at: https://console.groq.com

ROBUST VERSION: Separate calls for research vs blog writing,
with plain-text blog generation (no JSON parsing issues).
"""

import os
import json
import re
from flask import Flask, request, jsonify, render_template
from urllib.request import urlopen, Request
from urllib.error import URLError

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"


def call_groq(prompt: str, max_tokens: int = 4096) -> str:
    """Call Groq API. Raises on error so we see real error messages."""
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set. Get free key at https://console.groq.com "
            "then add to Render > Environment > GROQ_API_KEY"
        )
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    req = Request(GROQ_URL, data=payload, headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }, method="POST")

    with urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


def parse_json_safe(raw: str, fallback: dict) -> dict:
    """Try to extract and parse JSON from a response, return fallback on failure."""
    # Remove markdown code fences
    cleaned = re.sub(r"```json\s*|```\s*", "", raw).strip()
    # Find the outermost { ... } block
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return fallback


# ─────────────────────────────────────────────
# AGENT 1 — Intent + Keywords + SERP (JSON)
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
    "question_keywords": ["What is {keyword}?", "How to {keyword}?", "Why {keyword} matters?"],
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
            "reasoning": "General topic", "user_goal": "Learn about the topic",
            "content_type": "Educational guide"
        },
        "keywords": {
            "primary_keyword": keyword,
            "secondary_keywords": [f"{keyword} guide", f"{keyword} tips", f"best {keyword}", f"{keyword} tutorial", f"{keyword} examples"],
            "long_tail_keywords": [f"how to {keyword}", f"best {keyword} for beginners", f"{keyword} step by step"],
            "lsi_keywords": [f"{keyword} strategy", f"{keyword} techniques", f"{keyword} methods"],
            "question_keywords": [f"What is {keyword}?", f"How does {keyword} work?", f"Why is {keyword} important?"],
            "search_volume_estimate": "medium", "competition_level": "medium"
        },
        "serp_gaps": {
            "common_topics_covered": ["Basic overview", "Common use cases", "Getting started"],
            "content_gaps": ["Practical examples", "Expert tips", "Common mistakes"],
            "unique_angles": ["Step-by-step walkthrough", "Real-world case study"],
            "competitor_weaknesses": ["Lack of examples", "Outdated info"],
            "our_opportunity": f"Most practical and complete guide on {keyword}",
            "recommended_word_count": 1500
        }
    })


# ─────────────────────────────────────────────
# AGENT 2 — Outline (JSON)
# ─────────────────────────────────────────────
def agent_outline(keyword: str, research: dict) -> dict:
    kws  = research.get("keywords", {})
    gaps = research.get("serp_gaps", {})
    sec  = ", ".join(kws.get("secondary_keywords", [])[:3])
    gap  = "; ".join(gaps.get("content_gaps", [])[:3])

    prompt = f"""Create an SEO blog outline for the keyword: "{keyword}"

Secondary keywords to include: {sec}
Content gaps to address: {gap}

Respond with ONLY raw JSON (no markdown, no explanation):
{{
  "h1_title": "Compelling title with '{keyword}'",
  "meta_description": "150-160 char meta description mentioning '{keyword}'",
  "intro_hook": "One sentence describing the opening hook",
  "sections": [
    {{"h2": "Section 1 Title", "purpose": "what it covers", "h3_subsections": ["Subsection A", "Subsection B"]}},
    {{"h2": "Section 2 Title", "purpose": "what it covers", "h3_subsections": ["Subsection A", "Subsection B"]}},
    {{"h2": "Section 3 Title", "purpose": "what it covers", "h3_subsections": ["Subsection A"]}},
    {{"h2": "Section 4 Title", "purpose": "what it covers", "h3_subsections": ["Subsection A", "Subsection B"]}},
    {{"h2": "Section 5 Title", "purpose": "what it covers", "h3_subsections": ["Subsection A"]}}
  ],
  "conclusion_summary": "What the conclusion covers",
  "estimated_read_time": "7 min read",
  "target_word_count": 1400
}}"""

    raw = call_groq(prompt, max_tokens=1000)
    return parse_json_safe(raw, {
        "h1_title": f"The Complete Guide to {keyword}: Everything You Need to Know",
        "meta_description": f"Learn everything about {keyword} with practical tips, expert advice, and step-by-step strategies. Your complete guide starts here.",
        "intro_hook": f"Hook about {keyword} and why it matters",
        "sections": [
            {"h2": f"What is {keyword}?", "purpose": "Definition and overview", "h3_subsections": ["Definition", "Why it matters"]},
            {"h2": f"How {keyword} Works", "purpose": "Mechanics and process", "h3_subsections": ["Core concepts", "Step by step"]},
            {"h2": f"Benefits of {keyword}", "purpose": "Key advantages", "h3_subsections": ["Top benefits"]},
            {"h2": f"How to Get Started with {keyword}", "purpose": "Practical guide", "h3_subsections": ["Step 1", "Step 2", "Step 3"]},
            {"h2": f"Common {keyword} Mistakes to Avoid", "purpose": "Pitfalls", "h3_subsections": ["Mistake 1", "Mistake 2"]},
        ],
        "conclusion_summary": "Recap and next steps",
        "estimated_read_time": "7 min read",
        "target_word_count": 1400
    })


# ─────────────────────────────────────────────
# AGENT 3 — Blog Writer (PLAIN TEXT — no JSON)
# ─────────────────────────────────────────────
def agent_write_blog(keyword: str, outline: dict, keywords: dict) -> str:
    """
    Writes the blog as plain markdown text — avoids JSON parsing issues
    that caused 'no content' problems.
    """
    sections_text = ""
    for s in outline.get("sections", []):
        sections_text += f"\n## {s.get('h2', '')}\n"
        for h3 in s.get("h3_subsections", []):
            sections_text += f"### {h3}\n"

    secondary = ", ".join(keywords.get("secondary_keywords", [])[:4])
    long_tail  = ", ".join(keywords.get("long_tail_keywords", [])[:2])

    prompt = f"""Write a complete, high-quality SEO blog post.

Title: {outline.get("h1_title", keyword)}
Primary keyword: "{keyword}"
Secondary keywords to use naturally: {secondary}
Long-tail keywords to include: {long_tail}

Follow this exact structure:
{sections_text}

Writing rules:
- Write 1300-1600 words total
- Start with a compelling 2-3 sentence intro (no heading)
- Use ## for H2 sections and ### for H3 subsections exactly as shown above
- Include the keyword "{keyword}" naturally every 150-200 words
- Write in a confident, friendly, expert tone
- Include specific practical examples and tips
- End with a strong conclusion paragraph and call to action
- NO clichés: never use "delve", "in today's fast-paced world", "it's worth noting", "leverage", "In conclusion"
- Use contractions naturally (you'll, it's, don't, we're)

Write the full blog post now in markdown format:"""

    return call_groq(prompt, max_tokens=4096)


# ─────────────────────────────────────────────
# AGENT 4 — Humanizer (PLAIN TEXT)
# ─────────────────────────────────────────────
def agent_humanize(blog: str, keyword: str) -> str:
    if len(blog.split()) < 200:
        return blog

    prompt = f"""Improve this blog post to sound more natural and human. Keep all ## and ### headings exactly as-is.

Rules:
- Keep keyword "{keyword}" throughout
- Use contractions (it's, you'll, don't)
- Mix short and long sentences
- Add 1-2 rhetorical questions
- Remove any remaining AI phrases
- Keep 1300-1600 words
- Keep all markdown ## and ### headings unchanged

Blog to improve:
---
{blog[:5000]}
---

Write the improved version in markdown (just the blog, nothing else):"""

    result = call_groq(prompt, max_tokens=4096)
    return result if result and len(result.split()) > 200 else blog


# ─────────────────────────────────────────────
# SEO SCORER (pure Python)
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

    score = 0
    recs  = []

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

    score = min(score, 100)
    return {
        "seo_score": score,
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
        # Agent 1: Research
        print(f"[1/4] Research — {keyword}")
        research = agent_research(keyword)

        # Agent 2: Outline
        print("[2/4] Outline")
        outline  = agent_outline(keyword, research)

        # Agent 3: Write blog (plain text — no JSON issues)
        print("[3/4] Writing blog")
        raw_blog = agent_write_blog(keyword, outline, research.get("keywords", {}))

        # Agent 4: Humanize
        print("[4/4] Humanizing")
        final_blog = agent_humanize(raw_blog, keyword)

        # Fallback: if humanized is empty, use raw
        if not final_blog or len(final_blog.split()) < 100:
            final_blog = raw_blog

        final_seo = seo_score(keyword, final_blog, outline)

        print(f"[DONE] {final_seo['word_count']} words, SEO score: {final_seo['seo_score']}")

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
    print("  AI Blog Engine — Powered by Groq (Free)")
    print("  Running at http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
