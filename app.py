"""
AI Blog Engine - Multi-Agent Blog Generation System
Backend: Flask + Google Gemini API (Free)

OPTIMIZED: 3 batched Gemini calls instead of 7 sequential ones.
Completes in ~20s — safe for Render free tier (30s timeout).
"""

import os
import json
import re
import time
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
# Primary key — set in Render > Environment
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")
# Optional backup key from a second Google account (leave blank if unused)
GEMINI_API_KEY2 = os.environ.get("GEMINI_API_KEY2", "")

_models = {}  # cache per key

def get_model(key: str):
    if key in _models:
        return _models[key]
    genai.configure(api_key=key)
    _models[key] = genai.GenerativeModel("gemini-2.0-flash")
    return _models[key]


def call_gemini(prompt: str, retries: int = 3) -> str:
    """Call Gemini. On 429, auto-switch to backup key if available."""
    keys = [k for k in [GEMINI_API_KEY, GEMINI_API_KEY2] if k]
    if not keys:
        raise ValueError(
            "GEMINI_API_KEY not set. Render > your service > Environment > add GEMINI_API_KEY."
        )
    last_err = None
    for key in keys:
        m = get_model(key)
        for attempt in range(retries):
            try:
                response = m.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                msg = str(e)
                is_rate = "429" in msg or "quota" in msg.lower() or "rate" in msg.lower()
                if is_rate and attempt < retries - 1:
                    wait = 5 * (attempt + 1)
                    print(f"[Rate limit on key ...{key[-6:]}] waiting {wait}s...")
                    time.sleep(wait)
                elif is_rate:
                    last_err = e
                    print(f"[Key ...{key[-6:]}] exhausted, trying backup key...")
                    break  # try next key
                else:
                    raise  # non-rate errors bubble up immediately
    raise RuntimeError(
        "429 Rate limit exceeded on all keys. Wait 1 minute and try again. "
        "Tip: add GEMINI_API_KEY2 in Render Environment with a key from a second Google account."
    )


# ── BATCH CALL 1: Intent + Keywords + SERP Gap (3 agents, 1 API call)
def batch_research(keyword: str) -> dict:
    prompt = f"""
You are a multi-agent SEO research system. For the keyword "{keyword}", run all three
agents below and return ONE valid JSON object containing all results.

Return ONLY this JSON (no markdown fences, no extra text):
{{
  "intent": {{
    "intent_type": "informational|commercial|transactional|navigational",
    "confidence": "high|medium|low",
    "reasoning": "brief reason",
    "user_goal": "what user wants to achieve",
    "content_type": "best content type e.g. how-to guide"
  }},
  "keywords": {{
    "primary_keyword": "{keyword}",
    "secondary_keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"],
    "long_tail_keywords": ["phrase1", "phrase2", "phrase3", "phrase4"],
    "lsi_keywords": ["lsi1", "lsi2", "lsi3"],
    "question_keywords": ["What is...?", "How to...?", "Why does...?", "When should...?"],
    "search_volume_estimate": "high|medium|low",
    "competition_level": "high|medium|low"
  }},
  "serp_gaps": {{
    "common_topics_covered": ["topic1", "topic2", "topic3"],
    "content_gaps": ["Gap 1: ...", "Gap 2: ...", "Gap 3: ..."],
    "unique_angles": ["Angle 1", "Angle 2", "Angle 3"],
    "competitor_weaknesses": ["Weakness 1", "Weakness 2"],
    "our_opportunity": "The biggest content opportunity in one sentence",
    "recommended_word_count": 1600
  }}
}}
"""
    raw = call_gemini(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {
            "intent": {
                "intent_type": "informational", "confidence": "medium",
                "reasoning": "Analysis complete", "user_goal": "Learn about the topic",
                "content_type": "Educational guide"
            },
            "keywords": {
                "primary_keyword": keyword, "secondary_keywords": [],
                "long_tail_keywords": [], "lsi_keywords": [], "question_keywords": [],
                "search_volume_estimate": "medium", "competition_level": "medium"
            },
            "serp_gaps": {
                "common_topics_covered": [], "content_gaps": ["Depth", "Examples", "Stats"],
                "unique_angles": [], "competitor_weaknesses": [],
                "our_opportunity": "Comprehensive coverage", "recommended_word_count": 1600
            }
        }


# ── BATCH CALL 2: Outline + Blog (2 agents, 1 API call)
def batch_outline_and_blog(keyword: str, research: dict) -> dict:
    kws       = research.get("keywords", {})
    gaps      = research.get("serp_gaps", {})
    secondary = ", ".join(kws.get("secondary_keywords", [])[:4])
    long_tail = ", ".join(kws.get("long_tail_keywords", [])[:3])
    gap_list  = "\n".join(f"- {g}" for g in gaps.get("content_gaps", []))
    angles    = "\n".join(f"- {a}" for a in gaps.get("unique_angles", []))

    prompt = f"""
You are a dual-mode SEO content system. For the keyword "{keyword}", complete TWO tasks
and return ONE JSON object.

Context:
- Secondary keywords: {secondary}
- Long-tail keywords: {long_tail}
- Content gaps:
{gap_list}
- Unique angles:
{angles}

TASK 1: Create the SEO blog outline.
TASK 2: Write the full blog post following that outline.

Blog rules:
- 1200-1500 words
- Use ## for H2 headings, ### for H3
- Use "{keyword}" naturally throughout
- Conversational expert tone with personality
- No cliches: no "In conclusion", "In today's world", "Delve into"
- Include practical tips and real examples

Return ONLY this JSON (no markdown fences, no extra text):
{{
  "outline": {{
    "h1_title": "Compelling SEO title containing the keyword",
    "meta_description": "150-160 char meta description with keyword",
    "intro_hook": "One sentence hook",
    "sections": [
      {{
        "h2": "Section heading",
        "purpose": "what this section covers",
        "h3_subsections": ["Subsection 1", "Subsection 2"]
      }}
    ],
    "conclusion_summary": "What the conclusion covers",
    "estimated_read_time": "7 min read",
    "target_word_count": 1400
  }},
  "blog": "FULL BLOG POST IN MARKDOWN. Use actual newline characters for line breaks."
}}
"""
    raw = call_gemini(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {
            "outline": {
                "h1_title": f"The Complete Guide to {keyword}",
                "meta_description": f"Everything about {keyword}: expert tips, strategies, and practical advice you can use today.",
                "intro_hook": f"Introduction to {keyword}",
                "sections": [],
                "conclusion_summary": "Key takeaways",
                "estimated_read_time": "7 min read",
                "target_word_count": 1400
            },
            "blog": raw
        }


# ── BATCH CALL 3: Humanizer (1 API call)
def humanize_blog(blog_content: str, keyword: str) -> str:
    if len(blog_content.split()) < 100:
        return blog_content

    prompt = f"""
Rewrite the blog below to sound genuinely human — confident, warm, expert.
Keep all markdown headings (## and ###) and the keyword "{keyword}".

Rules:
- Keep 1200-1500 words
- Vary sentence length dramatically
- Use contractions naturally (it's, you'll, don't, we're)
- Remove AI cliches (delve, It's worth noting, In today's fast-paced world)
- Add one or two rhetorical questions
- Keep every ## and ### heading exactly as written

Blog:
---
{blog_content[:5000]}
---

Write the humanized version in markdown now (no JSON, just the blog text):
"""
    result = call_gemini(prompt)
    return result if result and len(result.split()) > 80 else blog_content


# ── SEO Scorer (pure Python — no API call)
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
    elif wc >= 800:  score += 12; recs.append("Increase word count above 1200 for better SEO.")
    else:            score += 5;  recs.append("Content too short — aim for 1200+ words.")

    if 0.5 <= density <= 2.5:  score += 20
    elif density < 0.5:        score += 8;  recs.append(f"Low keyword density ({density}%). Use '{keyword}' more naturally.")
    else:                      score += 8;  recs.append(f"High keyword density ({density}%). Reduce repetition.")

    if has_h2 and has_h3:  score += 20
    elif has_h2:           score += 12; recs.append("Add H3 subheadings for better structure.")
    else:                  recs.append("Missing H2/H3 headings — add proper structure.")

    if 140 <= meta_len <= 160:   score += 20
    elif 100 <= meta_len < 140:  score += 12; recs.append("Meta description slightly short (aim 150-160 chars).")
    elif meta_len > 160:         score += 10; recs.append("Meta description too long — trim to 160 chars.")
    else:                        score += 5;  recs.append("Meta description missing or too short.")

    if keyword.lower() in title.lower():  score += 10
    else:                                 recs.append("Add the primary keyword to the H1 title.")

    if wc > 0 and kw_count > 0:  score += 10

    score = min(score, 100)
    return {
        "seo_score": score,
        "word_count": wc,
        "keyword_count": kw_count,
        "keyword_density": density,
        "has_proper_headings": has_h2 and has_h3,
        "meta_description_length": meta_len,
        "recommendations": recs if recs else ["Great job! Content is well-optimized."],
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
    if not GEMINI_API_KEY:
        return jsonify({"error":
            "GEMINI_API_KEY not set. Render > your service > Environment > add GEMINI_API_KEY."}), 500

    try:
        print(f"[1/3] Research — {keyword}")
        research = batch_research(keyword)

        print("[2/3] Outline + Blog")
        content  = batch_outline_and_blog(keyword, research)
        outline  = content.get("outline", {})
        raw_blog = content.get("blog", "")

        print("[3/3] Humanize")
        final_blog = humanize_blog(raw_blog, keyword)
        final_seo  = seo_score(keyword, final_blog, outline)

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
