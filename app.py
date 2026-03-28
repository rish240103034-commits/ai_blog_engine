"""
AI Blog Engine - Multi-Agent Blog Generation System
Backend: Flask + Groq API (FREE, unlimited, ultra-fast)

Groq free tier: 30 req/min, 14,400 req/day — no credit card needed.
3 batched calls complete in ~8 seconds — well within Render's 30s limit.
"""

import os
import json
import re
from flask import Flask, request, jsonify, render_template
from urllib.request import urlopen, Request
from urllib.error import URLError
import urllib.parse

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION — Groq API (Free)
# Get your free key at: https://console.groq.com
# ─────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.3-70b-versatile"   # best free model on Groq


def call_groq(prompt: str) -> str:
    """
    Call Groq API using only Python stdlib (urllib) — no extra packages needed.
    Groq free tier: 30 req/min, 14,400 req/day, responses in ~1-2 seconds.
    """
    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not set. "
            "Get free key at https://console.groq.com → Render > Environment > GROQ_API_KEY"
        )

    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }).encode("utf-8")

    req = Request(
        GROQ_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST"
    )

    try:
        with urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except URLError as e:
        raise RuntimeError(f"Groq API error: {e.reason}")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Groq response parse error: {e}")


def safe_json(raw: str, fallback: dict) -> dict:
    """Strip markdown fences and parse JSON safely."""
    cleaned = re.sub(r"```json|```", "", raw).strip()
    # Sometimes model wraps in extra text — extract the JSON object
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        cleaned = match.group(0)
    try:
        return json.loads(cleaned)
    except Exception:
        return fallback


# ─────────────────────────────────────────────
# CALL 1 — Research Agent (Intent + Keywords + SERP)
# ─────────────────────────────────────────────
def batch_research(keyword: str) -> dict:
    prompt = f"""You are an SEO research system. Analyze the keyword "{keyword}" and return ONE JSON object.

Return ONLY valid JSON (no markdown, no explanation):
{{
  "intent": {{
    "intent_type": "informational",
    "confidence": "high",
    "reasoning": "Users want to learn about this topic",
    "user_goal": "Understand and learn",
    "content_type": "How-to guide"
  }},
  "keywords": {{
    "primary_keyword": "{keyword}",
    "secondary_keywords": ["related term 1", "related term 2", "related term 3", "related term 4", "related term 5"],
    "long_tail_keywords": ["long tail phrase 1", "long tail phrase 2", "long tail phrase 3", "long tail phrase 4"],
    "lsi_keywords": ["semantic term 1", "semantic term 2", "semantic term 3"],
    "question_keywords": ["What is {keyword}?", "How to use {keyword}?", "Why is {keyword} important?", "When to use {keyword}?"],
    "search_volume_estimate": "high",
    "competition_level": "medium"
  }},
  "serp_gaps": {{
    "common_topics_covered": ["Basic overview", "Common use cases", "Getting started"],
    "content_gaps": ["In-depth practical examples", "Common mistakes to avoid", "Expert tips not found elsewhere"],
    "unique_angles": ["Real-world case studies", "Step-by-step actionable guide", "Comparison with alternatives"],
    "competitor_weaknesses": ["Lack of practical examples", "Outdated information"],
    "our_opportunity": "Create the most practical, up-to-date, example-rich guide on {keyword}",
    "recommended_word_count": 1500
  }}
}}"""

    raw = call_groq(prompt)
    return safe_json(raw, {
        "intent": {
            "intent_type": "informational", "confidence": "medium",
            "reasoning": "General topic research", "user_goal": "Learn about the topic",
            "content_type": "Educational guide"
        },
        "keywords": {
            "primary_keyword": keyword, "secondary_keywords": [keyword + " guide", keyword + " tips"],
            "long_tail_keywords": ["how to " + keyword, "best " + keyword + " strategies"],
            "lsi_keywords": [], "question_keywords": ["What is " + keyword + "?"],
            "search_volume_estimate": "medium", "competition_level": "medium"
        },
        "serp_gaps": {
            "common_topics_covered": ["Overview", "Basics"],
            "content_gaps": ["Practical examples", "Expert insights"],
            "unique_angles": ["Step-by-step guide"],
            "competitor_weaknesses": ["Surface-level content"],
            "our_opportunity": "Comprehensive practical guide",
            "recommended_word_count": 1500
        }
    })


# ─────────────────────────────────────────────
# CALL 2 — Outline + Blog Generator
# ─────────────────────────────────────────────
def batch_outline_and_blog(keyword: str, research: dict) -> dict:
    kws       = research.get("keywords", {})
    gaps      = research.get("serp_gaps", {})
    secondary = ", ".join(kws.get("secondary_keywords", [])[:4])
    gap_list  = "; ".join(gaps.get("content_gaps", [])[:3])
    angles    = "; ".join(gaps.get("unique_angles", [])[:2])

    prompt = f"""You are an SEO content writer. For the keyword "{keyword}", write a complete blog post.

Context:
- Secondary keywords to include: {secondary}
- Content gaps to address: {gap_list}
- Unique angles: {angles}

Write a full 1200-1500 word blog post. Return ONLY valid JSON (no markdown fences):
{{
  "outline": {{
    "h1_title": "Engaging SEO title containing '{keyword}'",
    "meta_description": "Compelling 150-160 character meta description with '{keyword}'",
    "intro_hook": "One-line description of the intro hook",
    "sections": [
      {{"h2": "Section title", "purpose": "What it covers", "h3_subsections": ["Sub 1", "Sub 2"]}},
      {{"h2": "Section title 2", "purpose": "What it covers", "h3_subsections": ["Sub 1", "Sub 2"]}},
      {{"h2": "Section title 3", "purpose": "What it covers", "h3_subsections": ["Sub 1"]}},
      {{"h2": "Section title 4", "purpose": "What it covers", "h3_subsections": ["Sub 1", "Sub 2"]}},
      {{"h2": "Section title 5", "purpose": "What it covers", "h3_subsections": ["Sub 1"]}}
    ],
    "conclusion_summary": "Brief conclusion description",
    "estimated_read_time": "7 min read",
    "target_word_count": 1400
  }},
  "blog": "# H1 Title Here\\n\\nIntroduction paragraph here...\\n\\n## Section 1\\n\\nContent here...\\n\\n### Subsection\\n\\nContent...\\n\\n## Section 2\\n\\nMore content... (write full 1200-1500 word blog in markdown using \\\\n for newlines)"
}}

IMPORTANT: The blog field must contain the COMPLETE blog post in markdown format with proper ## and ### headings, at least 1200 words, practical examples, and the keyword '{keyword}' used naturally throughout."""

    raw = call_groq(prompt)
    result = safe_json(raw, {})

    # Fallback if blog field is missing or too short
    if not result.get("blog") or len(result.get("blog","").split()) < 200:
        result["blog"] = raw  # use raw text as blog

    if not result.get("outline"):
        result["outline"] = {
            "h1_title": f"The Complete Guide to {keyword}",
            "meta_description": f"Discover everything about {keyword} with expert tips, practical examples, and actionable strategies you can use today.",
            "intro_hook": f"Hook about {keyword}",
            "sections": [],
            "conclusion_summary": "Key takeaways",
            "estimated_read_time": "7 min read",
            "target_word_count": 1400
        }

    return result


# ─────────────────────────────────────────────
# CALL 3 — Humanizer Agent
# ─────────────────────────────────────────────
def humanize_blog(blog_content: str, keyword: str) -> str:
    word_count = len(blog_content.split())
    if word_count < 150:
        return blog_content

    prompt = f"""Rewrite this blog post to sound authentically human — expert, warm, and engaging.

Rules:
- Keep ALL ## and ### markdown headings exactly as they are
- Keep the keyword "{keyword}" throughout
- Use contractions (it's, you'll, don't, we're, they're)
- Vary sentence length: mix short punchy sentences with longer detailed ones
- Remove all AI clichés: "delve into", "in today's fast-paced world", "it's worth noting", "leverage"
- Add 1-2 rhetorical questions to engage readers
- Keep 1200-1400 words
- Maintain all practical examples and tips

Blog to humanize:
---
{blog_content[:5500]}
---

Write ONLY the humanized blog in markdown (no JSON, no explanation):"""

    result = call_groq(prompt)
    # Only use result if it's a real blog (not empty/error)
    if result and len(result.split()) > 150:
        return result
    return blog_content


# ─────────────────────────────────────────────
# SEO SCORER (pure Python — instant, no API)
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

    if wc > 0 and kw_count > 0: score += 10

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
    if not GROQ_API_KEY:
        return jsonify({"error":
            "GROQ_API_KEY not set. Get free key at https://console.groq.com "
            "then add it in Render > your service > Environment."}), 500

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
    print("  AI Blog Engine — Powered by Groq (Free)")
    print("  Running at http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
