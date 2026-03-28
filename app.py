"""
AI Blog Engine - Multi-Agent Blog Generation System
Backend: Flask + Google Gemini API (Free)
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Lazy-load model so missing key doesn't crash on startup
model = None

def get_model():
    """Initialize Gemini model lazily — safe for cold starts on Render."""
    global model
    if model is not None:
        return model
    key = GEMINI_API_KEY
    if not key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. "
                         "Add it in Render → your service → Environment tab.")
    genai.configure(api_key=key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    return model


def call_gemini(prompt: str, retries: int = 4) -> str:
    """Call Gemini API with automatic retry + exponential backoff on rate limit."""
    m = get_model()
    for attempt in range(retries):
        try:
            response = m.generate_content(prompt)
            time.sleep(4)  # 4s gap between calls to stay within free quota
            return response.text.strip()
        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                wait = 15 * (attempt + 1)  # 15s, 30s, 45s, 60s
                print(f"[Rate limit] Waiting {wait}s before retry {attempt+1}/{retries}...")
                time.sleep(wait)
            else:
                return f"ERROR: {msg}"
    return "ERROR: Rate limit exceeded after retries. Wait 1 minute and try again."


# ─────────────────────────────────────────────
# AGENT 1: Intent Analyzer
# ─────────────────────────────────────────────
def intent_analyzer_agent(keyword: str) -> dict:
    """
    Analyzes the search intent behind a keyword.
    Returns intent type and confidence reasoning.
    """
    prompt = f"""
You are an expert SEO Intent Analyzer Agent.

Analyze the search intent for the keyword: "{keyword}"

Respond ONLY in valid JSON format like this:
{{
  "intent_type": "informational|commercial|transactional|navigational",
  "confidence": "high|medium|low",
  "reasoning": "Brief explanation of why this intent was classified this way",
  "user_goal": "What the user is trying to achieve",
  "content_type": "What type of content best serves this intent (e.g., how-to guide, product comparison, listicle)"
}}

Return ONLY the JSON, no extra text.
"""
    raw = call_gemini(prompt)
    try:
        # Strip markdown code fences if present
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception:
        return {
            "intent_type": "informational",
            "confidence": "medium",
            "reasoning": raw,
            "user_goal": "Learn about the topic",
            "content_type": "Educational guide"
        }


# ─────────────────────────────────────────────
# AGENT 2: Keyword Clustering
# ─────────────────────────────────────────────
def keyword_clustering_agent(keyword: str, intent: dict) -> dict:
    """
    Generates a full keyword cluster around the primary keyword.
    """
    prompt = f"""
You are an expert SEO Keyword Research Agent.

Primary Keyword: "{keyword}"
Search Intent: {intent.get("intent_type", "informational")}

Generate a comprehensive keyword cluster. Respond ONLY in valid JSON:
{{
  "primary_keyword": "{keyword}",
  "secondary_keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "long_tail_keywords": [
    "long tail phrase 1",
    "long tail phrase 2",
    "long tail phrase 3",
    "long tail phrase 4",
    "long tail phrase 5"
  ],
  "lsi_keywords": ["semantic keyword1", "semantic keyword2", "semantic keyword3"],
  "question_keywords": [
    "What is...",
    "How to...",
    "Why does...",
    "When should..."
  ],
  "search_volume_estimate": "high|medium|low",
  "competition_level": "high|medium|low"
}}

Return ONLY the JSON, no extra text.
"""
    raw = call_gemini(prompt)
    try:
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception:
        return {
            "primary_keyword": keyword,
            "secondary_keywords": [],
            "long_tail_keywords": [],
            "lsi_keywords": [],
            "question_keywords": [],
            "search_volume_estimate": "medium",
            "competition_level": "medium"
        }


# ─────────────────────────────────────────────
# AGENT 3: SERP Gap Analysis
# ─────────────────────────────────────────────
def serp_gap_analysis_agent(keyword: str, keywords: dict) -> dict:
    """
    Identifies content gaps and opportunities vs. competitor blogs.
    """
    secondary = ", ".join(keywords.get("secondary_keywords", [])[:3])
    prompt = f"""
You are an expert SERP Gap Analysis Agent for content strategy.

Primary Keyword: "{keyword}"
Related Keywords: {secondary}

Analyze what content gaps exist in typical top-ranking articles for this keyword.
Respond ONLY in valid JSON:
{{
  "common_topics_covered": ["topic1", "topic2", "topic3"],
  "content_gaps": [
    "Gap 1: What most articles miss...",
    "Gap 2: Rarely covered angle...",
    "Gap 3: Missing depth on..."
  ],
  "unique_angles": [
    "Unique angle 1",
    "Unique angle 2",
    "Unique angle 3"
  ],
  "competitor_weaknesses": [
    "Weakness 1",
    "Weakness 2"
  ],
  "our_opportunity": "Summary of the biggest content opportunity to outrank competitors",
  "recommended_word_count": 1500
}}

Return ONLY the JSON, no extra text.
"""
    raw = call_gemini(prompt)
    try:
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception:
        return {
            "common_topics_covered": [],
            "content_gaps": ["Depth of explanation", "Practical examples", "Latest statistics"],
            "unique_angles": [],
            "competitor_weaknesses": [],
            "our_opportunity": raw,
            "recommended_word_count": 1500
        }


# ─────────────────────────────────────────────
# AGENT 4: Outline Generator
# ─────────────────────────────────────────────
def outline_generator_agent(keyword: str, keywords: dict, gaps: dict) -> dict:
    """
    Creates a fully SEO-optimized blog outline with H1/H2/H3 structure.
    """
    gaps_text = "\n".join(gaps.get("content_gaps", []))
    angles_text = "\n".join(gaps.get("unique_angles", []))
    prompt = f"""
You are an expert Blog Outline Architect Agent.

Primary Keyword: "{keyword}"
Secondary Keywords: {", ".join(keywords.get("secondary_keywords", [])[:4])}
Content Gaps to Address:
{gaps_text}
Unique Angles:
{angles_text}

Create a fully SEO-optimized blog outline. Respond ONLY in valid JSON:
{{
  "h1_title": "Compelling, keyword-rich H1 title",
  "meta_description": "150-160 character meta description with primary keyword",
  "intro_hook": "One sentence describing what the intro paragraph will cover",
  "sections": [
    {{
      "h2": "Section heading",
      "purpose": "What this section covers",
      "h3_subsections": ["Subsection 1", "Subsection 2"]
    }}
  ],
  "conclusion_summary": "What the conclusion will wrap up",
  "estimated_read_time": "X min read",
  "target_word_count": 1800
}}

Include 5-7 H2 sections with 2-3 H3 subsections each.
Return ONLY the JSON, no extra text.
"""
    raw = call_gemini(prompt)
    try:
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception:
        return {
            "h1_title": f"Complete Guide to {keyword}",
            "meta_description": f"Learn everything about {keyword} in this comprehensive guide.",
            "intro_hook": "Introduction to the topic",
            "sections": [],
            "conclusion_summary": "Summary",
            "estimated_read_time": "8 min read",
            "target_word_count": 1800
        }


# ─────────────────────────────────────────────
# AGENT 5: Blog Generator
# ─────────────────────────────────────────────
def blog_generator_agent(keyword: str, keywords: dict, outline: dict) -> str:
    """
    Generates the full blog post following the outline and keyword targets.
    """
    sections_text = ""
    for s in outline.get("sections", []):
        sections_text += f"\n- H2: {s.get('h2', '')}"
        for h3 in s.get("h3_subsections", []):
            sections_text += f"\n  - H3: {h3}"

    prompt = f"""
You are an expert Blog Content Writer Agent. Write a full, engaging, SEO-optimized blog post.

Title: {outline.get("h1_title", keyword)}
Primary Keyword: "{keyword}"
Secondary Keywords: {", ".join(keywords.get("secondary_keywords", [])[:5])}
Long-tail Keywords: {", ".join(keywords.get("long_tail_keywords", [])[:3])}

Blog Structure to Follow:
{sections_text}

Requirements:
- Write 1500-2000 words
- Use markdown formatting (## for H2, ### for H3)
- Include the primary keyword naturally every 150-200 words
- Add a compelling introduction with a hook
- Include practical examples and actionable tips
- Add a strong conclusion with a call to action
- Do NOT use generic phrases like "In conclusion" or "In summary"
- Write in a confident, authoritative yet conversational tone
- Include relevant statistics or data points where appropriate

Start writing the full blog post now:
"""
    return call_gemini(prompt)


# ─────────────────────────────────────────────
# AGENT 6: SEO Optimizer
# ─────────────────────────────────────────────
def seo_optimizer_agent(keyword: str, blog_content: str, outline: dict) -> dict:
    """
    Analyzes the generated blog for SEO quality and returns a score + recommendations.
    """
    word_count = len(blog_content.split())
    keyword_count = blog_content.lower().count(keyword.lower())
    keyword_density = round((keyword_count / max(word_count, 1)) * 100, 2)
    has_h2 = "##" in blog_content and "###" not in blog_content[:5]
    has_h3 = "###" in blog_content
    meta_desc = outline.get("meta_description", "")
    meta_length = len(meta_desc)

    # Scoring logic
    score = 0
    recommendations = []

    # Word count score (max 20)
    if word_count >= 1500:
        score += 20
    elif word_count >= 1000:
        score += 12
        recommendations.append("Increase word count to at least 1500 for better ranking potential.")
    else:
        score += 5
        recommendations.append("Content is too short. Aim for 1500+ words.")

    # Keyword density score (max 20)
    if 0.5 <= keyword_density <= 2.5:
        score += 20
    elif keyword_density < 0.5:
        score += 8
        recommendations.append(f"Keyword density is low ({keyword_density}%). Use '{keyword}' more naturally.")
    else:
        score += 8
        recommendations.append(f"Keyword density is high ({keyword_density}%). Reduce keyword stuffing.")

    # Headings score (max 20)
    if has_h2 and has_h3:
        score += 20
    elif has_h2:
        score += 12
        recommendations.append("Add H3 subheadings to improve content structure.")
    else:
        score += 0
        recommendations.append("Missing H2 and H3 headings. Use proper heading hierarchy.")

    # Meta description score (max 20)
    if 140 <= meta_length <= 160:
        score += 20
    elif 100 <= meta_length < 140:
        score += 12
        recommendations.append("Meta description could be slightly longer (aim for 150-160 chars).")
    elif meta_length > 160:
        score += 10
        recommendations.append("Meta description is too long. Keep it under 160 characters.")
    else:
        score += 5
        recommendations.append("Meta description is missing or too short.")

    # Keyword in title (max 10)
    if keyword.lower() in outline.get("h1_title", "").lower():
        score += 10
    else:
        recommendations.append("Include the primary keyword in the H1 title.")

    # Content quality heuristic (max 10)
    if word_count > 0 and keyword_count > 0:
        score += 10

    return {
        "seo_score": min(score, 100),
        "word_count": word_count,
        "keyword_count": keyword_count,
        "keyword_density": keyword_density,
        "has_proper_headings": has_h2 and has_h3,
        "meta_description_length": meta_length,
        "recommendations": recommendations if recommendations else ["Great job! Your content is well-optimized."],
        "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D"
    }


# ─────────────────────────────────────────────
# AGENT 7: Humanizer Agent
# ─────────────────────────────────────────────
def humanizer_agent(blog_content: str, keyword: str) -> str:
    """
    Rewrites content to sound more natural and human-like,
    reducing AI detection patterns.
    """
    prompt = f"""
You are an expert Content Humanizer Agent. Your job is to rewrite AI-generated content 
to sound authentically human, while keeping all the SEO value and information intact.

Here is the blog post to humanize:

---
{blog_content}
---

Rewriting Rules:
1. Replace overly formal or robotic phrases with natural language
2. Add personality — occasional humor, rhetorical questions, relatable analogies
3. Vary sentence length dramatically (mix short punchy sentences with longer ones)
4. Remove clichés like "In today's fast-paced world", "Delve into", "In conclusion"
5. Add first-person perspective where appropriate ("I've seen...", "In my experience...")
6. Use contractions naturally (it's, you'll, don't, we're)
7. Keep all markdown headings (## and ###) and structure intact
8. Keep the primary keyword "{keyword}" in the content
9. Target 1500-2000 words
10. Make it sound like an expert who genuinely enjoys the topic

Write the humanized version now (markdown format):
"""
    return call_gemini(prompt)


# ─────────────────────────────────────────────
# MAIN API ENDPOINT
# ─────────────────────────────────────────────
@app.route("/generate", methods=["POST"])
def generate():
    """
    Main endpoint that orchestrates all 7 agents in sequence.
    Accepts: { "keyword": "your keyword here" }
    Returns: Full JSON with all agent outputs
    """
    data = request.get_json()
    if not data or "keyword" not in data:
        return jsonify({"error": "Missing 'keyword' in request body"}), 400

    keyword = data["keyword"].strip()
    if not keyword:
        return jsonify({"error": "Keyword cannot be empty"}), 400

    if len(keyword) > 200:
        return jsonify({"error": "Keyword too long (max 200 characters)"}), 400

    try:
        # Validate API key early — return clear JSON error, not HTML crash
        if not GEMINI_API_KEY:
            return jsonify({"error": "GEMINI_API_KEY is not set on the server. "
                            "Go to Render → your service → Environment → add GEMINI_API_KEY."}), 500

        # ── Agent 1: Intent Analysis
        print(f"[Agent 1] Analyzing intent for: {keyword}")
        intent = intent_analyzer_agent(keyword)

        # ── Agent 2: Keyword Clustering
        print("[Agent 2] Generating keyword cluster...")
        keywords = keyword_clustering_agent(keyword, intent)

        # ── Agent 3: SERP Gap Analysis
        print("[Agent 3] Running SERP gap analysis...")
        serp_gaps = serp_gap_analysis_agent(keyword, keywords)

        # ── Agent 4: Outline Generation
        print("[Agent 4] Generating blog outline...")
        outline = outline_generator_agent(keyword, keywords, serp_gaps)

        # ── Agent 5: Blog Generation
        print("[Agent 5] Writing full blog content...")
        raw_blog = blog_generator_agent(keyword, keywords, outline)

        # ── Agent 6: SEO Optimization Check
        print("[Agent 6] Running SEO optimization analysis...")
        seo_report = seo_optimizer_agent(keyword, raw_blog, outline)

        # ── Agent 7: Humanize Content
        print("[Agent 7] Humanizing content...")
        final_blog = humanizer_agent(raw_blog, keyword)

        # Re-run SEO check on humanized content
        final_seo = seo_optimizer_agent(keyword, final_blog, outline)

        return jsonify({
            "success": True,
            "keyword": keyword,
            "intent": intent,
            "keywords": keywords,
            "serp_gaps": serp_gaps,
            "outline": outline,
            "seo_report": final_seo,
            "final_blog": final_blog
        })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({"error": f"Generation failed: {str(e)}"}), 500


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    print("=" * 50)
    print("  AI Blog Engine — Multi-Agent System")
    print("  Running at http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
