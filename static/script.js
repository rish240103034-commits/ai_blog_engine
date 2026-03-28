/**
 * AI Blog Engine — Frontend Script
 * Handles API calls, rendering, tabs, theme, and clipboard
 */

// ─────────────────────────────────────────────
// STATE
// ─────────────────────────────────────────────
let currentData = null;
let isGenerating = false;

// ─────────────────────────────────────────────
// DOM REFS
// ─────────────────────────────────────────────
const keywordInput    = document.getElementById("keywordInput");
const generateBtn     = document.getElementById("generateBtn");
const loadingSection  = document.getElementById("loadingSection");
const resultsSection  = document.getElementById("resultsSection");
const errorSection    = document.getElementById("errorSection");
const errorMessage    = document.getElementById("errorMessage");
const retryBtn        = document.getElementById("retryBtn");
const themeToggle     = document.getElementById("themeToggle");
const copyBtn         = document.getElementById("copyBtn");
const downloadBtn     = document.getElementById("downloadBtn");
const toast           = document.getElementById("toast");

// ─────────────────────────────────────────────
// THEME TOGGLE
// ─────────────────────────────────────────────
themeToggle.addEventListener("click", () => {
  const html = document.documentElement;
  const current = html.getAttribute("data-theme");
  html.setAttribute("data-theme", current === "dark" ? "light" : "dark");
});

// ─────────────────────────────────────────────
// TOAST NOTIFICATION
// ─────────────────────────────────────────────
function showToast(msg, type = "success") {
  toast.textContent = msg;
  toast.className = `toast ${type} show`;
  setTimeout(() => { toast.className = "toast"; }, 3000);
}

// ─────────────────────────────────────────────
// LOADING ANIMATION STATE MACHINE
// ─────────────────────────────────────────────
const loadingMessages = [
  { title: "Analyzing Intent...",       sub: "Agent 01 classifying keyword intent",         step: 1 },
  { title: "Clustering Keywords...",    sub: "Agent 02 generating keyword variations",       step: 2 },
  { title: "Scanning SERP Gaps...",     sub: "Agent 03 identifying content opportunities",  step: 3 },
  { title: "Building Outline...",       sub: "Agent 04 architecting blog structure",         step: 4 },
  { title: "Writing Content...",        sub: "Agent 05 generating full blog post",           step: 5 },
  { title: "Optimizing for SEO...",     sub: "Agent 06 analyzing keyword density & structure", step: 6 },
  { title: "Humanizing Content...",     sub: "Agent 07 removing AI patterns",               step: 7 },
];

let loadingInterval = null;
let loadingIndex = 0;

function startLoadingAnimation() {
  loadingIndex = 0;
  // Reset all steps
  for (let i = 1; i <= 7; i++) {
    const el = document.getElementById(`ls-${i}`);
    const st = document.getElementById(`lss-${i}`);
    el.className = "loading-step";
    st.textContent = "waiting";
    // Reset pipeline dots
    const dot = document.querySelector(`[data-agent="${i}"]`);
    if (dot) dot.className = "agent-step";
  }
  updateLoadingStep(0);
  loadingInterval = setInterval(() => {
    loadingIndex++;
    if (loadingIndex < loadingMessages.length) {
      updateLoadingStep(loadingIndex);
    }
  }, 3500);
}

function updateLoadingStep(index) {
  const msg = loadingMessages[index];
  document.getElementById("loadingTitle").textContent = msg.title;
  document.getElementById("loadingSubtext").textContent = msg.sub;

  // Mark previous as done
  if (index > 0) {
    const prev = document.getElementById(`ls-${loadingMessages[index-1].step}`);
    const prevSt = document.getElementById(`lss-${loadingMessages[index-1].step}`);
    prev.className = "loading-step done";
    prevSt.textContent = "✓ done";
    const prevDot = document.querySelector(`[data-agent="${loadingMessages[index-1].step}"]`);
    if (prevDot) prevDot.className = "agent-step done";
  }

  // Mark current as running
  const curr = document.getElementById(`ls-${msg.step}`);
  const currSt = document.getElementById(`lss-${msg.step}`);
  curr.className = "loading-step running";
  currSt.textContent = "running...";
  const currDot = document.querySelector(`[data-agent="${msg.step}"]`);
  if (currDot) currDot.className = "agent-step active";
}

function stopLoadingAnimation() {
  clearInterval(loadingInterval);
  // Mark all as done
  for (let i = 1; i <= 7; i++) {
    const el = document.getElementById(`ls-${i}`);
    const st = document.getElementById(`lss-${i}`);
    el.className = "loading-step done";
    st.textContent = "✓ done";
    const dot = document.querySelector(`[data-agent="${i}"]`);
    if (dot) dot.className = "agent-step done";
  }
}

// ─────────────────────────────────────────────
// SECTION VISIBILITY
// ─────────────────────────────────────────────
function showSection(id) {
  loadingSection.style.display  = id === "loading"  ? "block" : "none";
  resultsSection.style.display  = id === "results"  ? "block" : "none";
  errorSection.style.display    = id === "error"    ? "block" : "none";
}

// ─────────────────────────────────────────────
// GENERATE BLOG
// ─────────────────────────────────────────────
async function generateBlog() {
  const keyword = keywordInput.value.trim();
  if (!keyword) {
    showToast("Please enter a keyword first", "error");
    keywordInput.focus();
    return;
  }
  if (isGenerating) return;

  isGenerating = true;
  generateBtn.disabled = true;
  generateBtn.querySelector(".btn-text").textContent = "Generating...";

  showSection("loading");
  startLoadingAnimation();

  // Scroll to loading
  loadingSection.scrollIntoView({ behavior: "smooth", block: "start" });

  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keyword })
    });

    const data = await response.json();

    stopLoadingAnimation();

    if (!response.ok || data.error) {
      throw new Error(data.error || "Unknown error occurred");
    }

    currentData = data;
    renderResults(data);
    showSection("results");
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    showToast("Blog generated successfully! ✓", "success");

  } catch (err) {
    stopLoadingAnimation();
    showSection("error");
    errorMessage.textContent = err.message || "Generation failed. Please check your API key and try again.";
    errorSection.scrollIntoView({ behavior: "smooth", block: "start" });
  } finally {
    isGenerating = false;
    generateBtn.disabled = false;
    generateBtn.querySelector(".btn-text").textContent = "Generate Blog";
  }
}

// ─────────────────────────────────────────────
// RENDER RESULTS
// ─────────────────────────────────────────────
function renderResults(data) {
  renderStatBar(data);
  renderResultsMeta(data);
  renderIntentPanel(data.intent);
  renderKeywordsPanel(data.keywords);
  renderSerpPanel(data.serp_gaps);
  renderOutlinePanel(data.outline);
  renderSeoPanel(data.seo_report, data.outline);
  renderBlogPanel(data.final_blog, data.seo_report);
  // Reset to first tab
  activateTab("intent");
}

// ── Stats Bar
function renderStatBar(data) {
  const seo = data.seo_report;
  const gradeColors = { A: "stat-green", B: "stat-accent", C: "stat-gold", D: "stat-accent" };
  const gradeColor = gradeColors[seo.grade] || "stat-accent";
  document.getElementById("statsBar").innerHTML = `
    <div class="stat-card">
      <div class="stat-value ${gradeColor}">${seo.seo_score}<span style="font-size:16px;opacity:0.5">/100</span></div>
      <div class="stat-label">SEO Score</div>
    </div>
    <div class="stat-card">
      <div class="stat-value stat-accent">${seo.grade}</div>
      <div class="stat-label">Grade</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${seo.word_count.toLocaleString()}</div>
      <div class="stat-label">Word Count</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${seo.keyword_density}%</div>
      <div class="stat-label">Keyword Density</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">${data.outline.estimated_read_time || calcReadTime(seo.word_count)}</div>
      <div class="stat-label">Read Time</div>
    </div>
  `;
}

// ── Results Meta
function renderResultsMeta(data) {
  const intentColors = {
    informational: "#7c6aff", commercial: "#f0c060",
    transactional: "#5fe3a1", navigational: "#ff6b6b"
  };
  const c = intentColors[data.intent?.intent_type] || "#7c6aff";
  document.getElementById("resultsMeta").innerHTML = `
    <div class="meta-chip" style="color:${c}; border-color:${c}44">
      ${data.intent?.intent_type || "informational"}
    </div>
    <div class="meta-chip">
      ${data.keywords?.competition_level || "medium"} competition
    </div>
  `;
}

// ── Intent Panel
function renderIntentPanel(intent) {
  if (!intent) return;
  const type = (intent.intent_type || "informational").toLowerCase();
  document.getElementById("intentContent").innerHTML = `
    <div class="panel-grid">
      <div class="panel-card">
        <div class="panel-card-title">Classification</div>
        <div class="intent-badge intent-${type}">${type}</div>
        <div class="info-row">
          <span class="label">Confidence</span>
          <span class="value">${intent.confidence || "—"}</span>
        </div>
        <div class="info-row">
          <span class="label">Content Type</span>
          <span class="value">${intent.content_type || "—"}</span>
        </div>
        <div class="info-row">
          <span class="label">User Goal</span>
          <span class="value" style="text-align:right;max-width:55%">${intent.user_goal || "—"}</span>
        </div>
      </div>
      <div class="panel-card">
        <div class="panel-card-title">Reasoning</div>
        <p style="font-size:14px; color:var(--text-2); line-height:1.7">${intent.reasoning || "—"}</p>
      </div>
    </div>
  `;
}

// ── Keywords Panel
function renderKeywordsPanel(kws) {
  if (!kws) return;
  const secondary = (kws.secondary_keywords || []).map(k => `<span class="kw-tag secondary">${k}</span>`).join("");
  const longTail   = (kws.long_tail_keywords || []).map(k => `<span class="kw-tag">${k}</span>`).join("");
  const lsi        = (kws.lsi_keywords || []).map(k => `<span class="kw-tag">${k}</span>`).join("");
  const questions  = (kws.question_keywords || []).map(k => `<span class="kw-tag">${k}</span>`).join("");
  document.getElementById("keywordsContent").innerHTML = `
    <div class="panel-card" style="margin-bottom:16px">
      <div class="panel-card-title">Primary Keyword</div>
      <span class="kw-tag primary">${kws.primary_keyword}</span>
    </div>
    <div class="panel-grid">
      <div class="panel-card">
        <div class="panel-card-title">Secondary Keywords</div>
        <div class="keyword-tags">${secondary || "<span style='color:var(--text-3)'>None generated</span>"}</div>
      </div>
      <div class="panel-card">
        <div class="panel-card-title">Long-tail Keywords</div>
        <div class="keyword-tags">${longTail || "<span style='color:var(--text-3)'>None generated</span>"}</div>
      </div>
      <div class="panel-card">
        <div class="panel-card-title">LSI / Semantic Keywords</div>
        <div class="keyword-tags">${lsi || "<span style='color:var(--text-3)'>None generated</span>"}</div>
      </div>
      <div class="panel-card">
        <div class="panel-card-title">Question Keywords</div>
        <div class="keyword-tags">${questions || "<span style='color:var(--text-3)'>None generated</span>"}</div>
      </div>
    </div>
    <div class="panel-grid" style="margin-top:16px">
      <div class="panel-card">
        <div class="info-row"><span class="label">Search Volume</span><span class="value">${kws.search_volume_estimate || "—"}</span></div>
        <div class="info-row"><span class="label">Competition</span><span class="value">${kws.competition_level || "—"}</span></div>
      </div>
    </div>
  `;
}

// ── SERP Gap Panel
function renderSerpPanel(gaps) {
  if (!gaps) return;
  const gapItems    = (gaps.content_gaps || []).map(g => `<li class="gap-item"><span class="gap-bullet">◆</span><span>${g}</span></li>`).join("");
  const angleItems  = (gaps.unique_angles || []).map(a => `<li class="gap-item"><span class="gap-bullet" style="color:var(--accent-2)">◆</span><span>${a}</span></li>`).join("");
  const weakItems   = (gaps.competitor_weaknesses || []).map(w => `<li class="gap-item"><span class="gap-bullet" style="color:var(--accent-3)">◆</span><span>${w}</span></li>`).join("");
  document.getElementById("serpContent").innerHTML = `
    <div class="panel-card" style="margin-bottom:16px">
      <div class="panel-card-title">Our Biggest Opportunity</div>
      <p style="font-size:14px; color:var(--text-2); line-height:1.7">${gaps.our_opportunity || "—"}</p>
    </div>
    <div class="panel-grid">
      <div class="panel-card">
        <div class="panel-card-title">Content Gaps to Fill</div>
        <ul class="gap-list">${gapItems || "<li style='color:var(--text-3)'>None identified</li>"}</ul>
      </div>
      <div class="panel-card">
        <div class="panel-card-title">Unique Angles</div>
        <ul class="gap-list">${angleItems || "<li style='color:var(--text-3)'>None identified</li>"}</ul>
      </div>
      ${weakItems ? `<div class="panel-card">
        <div class="panel-card-title">Competitor Weaknesses</div>
        <ul class="gap-list">${weakItems}</ul>
      </div>` : ""}
    </div>
    <div style="margin-top:16px" class="panel-card">
      <div class="info-row">
        <span class="label">Recommended Word Count</span>
        <span class="value">${gaps.recommended_word_count || 1500}+ words</span>
      </div>
    </div>
  `;
}

// ── Outline Panel
function renderOutlinePanel(outline) {
  if (!outline) return;
  const sectionsHtml = (outline.sections || []).map(s => `
    <div class="outline-h2">
      <div class="outline-h2-title">${s.h2 || ""}</div>
      <div class="outline-h3s">
        ${(s.h3_subsections || []).map(h3 => `<div class="outline-h3">${h3}</div>`).join("")}
      </div>
    </div>
  `).join("");

  document.getElementById("outlineContent").innerHTML = `
    <div class="panel-card" style="margin-bottom:16px">
      <div class="panel-card-title">H1 Title</div>
      <p style="font-size:18px; font-weight:700; line-height:1.4">${outline.h1_title || "—"}</p>
    </div>
    <div class="panel-card" style="margin-bottom:16px">
      <div class="panel-card-title">Meta Description</div>
      <p style="font-size:14px; color:var(--text-2); line-height:1.7">${outline.meta_description || "—"}</p>
      <div style="margin-top:8px; font-size:12px; font-family:var(--font-mono); color:var(--text-3)">${(outline.meta_description || "").length} / 160 chars</div>
    </div>
    <div class="panel-card">
      <div class="panel-card-title">Blog Structure</div>
      <div class="outline-tree">${sectionsHtml || "<p style='color:var(--text-3)'>No outline generated</p>"}</div>
    </div>
  `;
}

// ── SEO Panel
function renderSeoPanel(seo, outline) {
  if (!seo) return;
  const score = seo.seo_score;
  const r = 52;
  const circ = 2 * Math.PI * r;
  const dash = circ - (score / 100) * circ;
  const gradeColor = { A: "#5fe3a1", B: "#7c6aff", C: "#f0c060", D: "#ff6b6b" }[seo.grade] || "#7c6aff";
  const recItems = (seo.recommendations || []).map(r => {
    const isGood = r.toLowerCase().includes("great job") || r.toLowerCase().includes("well-optimized");
    return `<li class="rec-item">
      <span class="rec-icon ${isGood ? "rec-good" : ""}">${isGood ? "✓" : "!"}</span>
      <span>${r}</span>
    </li>`;
  }).join("");

  document.getElementById("seoContent").innerHTML = `
    <div class="panel-card" style="margin-bottom:16px">
      <div class="seo-score-display">
        <div class="score-circle">
          <svg viewBox="0 0 120 120" width="120" height="120">
            <circle class="score-circle-bg" cx="60" cy="60" r="${r}" />
            <circle class="score-circle-fill"
              cx="60" cy="60" r="${r}"
              stroke="${gradeColor}"
              stroke-dasharray="${circ}"
              stroke-dashoffset="${dash}" />
          </svg>
          <div class="score-text">
            <div class="score-number" style="color:${gradeColor}">${score}</div>
            <div class="score-label">/ 100</div>
          </div>
        </div>
        <div class="score-details">
          <div class="score-grade" style="color:${gradeColor}">${seo.grade}</div>
          <div class="score-summary">
            ${score >= 85 ? "Excellent! This content is well-optimized for search engines." :
              score >= 70 ? "Good optimization. A few tweaks can push this higher." :
              score >= 55 ? "Moderate optimization. Several areas need improvement." :
              "Needs significant SEO improvements before publishing."}
          </div>
        </div>
      </div>
    </div>
    <div class="seo-metrics">
      <div class="seo-metric">
        <div class="seo-metric-name">Word Count</div>
        <div class="seo-metric-value">${seo.word_count.toLocaleString()}</div>
      </div>
      <div class="seo-metric">
        <div class="seo-metric-name">Keyword Uses</div>
        <div class="seo-metric-value">${seo.keyword_count}</div>
      </div>
      <div class="seo-metric">
        <div class="seo-metric-name">Density</div>
        <div class="seo-metric-value">${seo.keyword_density}%</div>
      </div>
      <div class="seo-metric">
        <div class="seo-metric-name">Headings</div>
        <div class="seo-metric-value">${seo.has_proper_headings ? "✓" : "✗"}</div>
      </div>
      <div class="seo-metric">
        <div class="seo-metric-name">Meta Length</div>
        <div class="seo-metric-value">${seo.meta_description_length} ch</div>
      </div>
    </div>
    <div class="panel-card">
      <div class="panel-card-title">Recommendations</div>
      <ul class="rec-list">${recItems}</ul>
    </div>
  `;
}

// ── Blog Panel
function renderBlogPanel(blogMarkdown, seo) {
  const html = markdownToHtml(blogMarkdown || "");
  const wordCount = seo?.word_count || (blogMarkdown || "").split(/\s+/).length;
  const readTime  = calcReadTime(wordCount);

  document.getElementById("wordCountBadge").textContent = `${wordCount.toLocaleString()} words`;
  document.getElementById("readTimeBadge").textContent   = readTime;
  document.getElementById("blogContent").innerHTML       = html;
}

// ─────────────────────────────────────────────
// MARKDOWN → HTML (minimal parser)
// ─────────────────────────────────────────────
function markdownToHtml(md) {
  if (!md) return "";
  return md
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm,  "<h2>$1</h2>")
    .replace(/^# (.+)$/gm,   "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g,     "<em>$1</em>")
    .replace(/`(.+?)`/g,       "<code>$1</code>")
    .replace(/^\> (.+)$/gm,    "<blockquote>$1</blockquote>")
    .replace(/^\* (.+)$/gm,    "<li>$1</li>")
    .replace(/^- (.+)$/gm,     "<li>$1</li>")
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n\n/g, "</p><p>")
    .replace(/^([^<\n].+)$/gm, m => m.startsWith("<") ? m : `<p>${m}</p>`)
    .replace(/<p><\/p>/g, "");
}

// ─────────────────────────────────────────────
// UTILITY
// ─────────────────────────────────────────────
function calcReadTime(wordCount) {
  const mins = Math.ceil(wordCount / 200);
  return `${mins} min read`;
}

// ─────────────────────────────────────────────
// TAB SYSTEM
// ─────────────────────────────────────────────
function activateTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tabId);
  });
  document.querySelectorAll(".tab-panel").forEach(panel => {
    panel.classList.toggle("active", panel.id === `panel-${tabId}`);
  });
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => activateTab(btn.dataset.tab));
});

// ─────────────────────────────────────────────
// COPY & DOWNLOAD
// ─────────────────────────────────────────────
copyBtn.addEventListener("click", () => {
  if (!currentData?.final_blog) { showToast("No content to copy", "error"); return; }
  navigator.clipboard.writeText(currentData.final_blog)
    .then(() => {
      copyBtn.innerHTML = "<span>✓</span> Copied!";
      showToast("Blog copied to clipboard!", "success");
      setTimeout(() => { copyBtn.innerHTML = "<span>⧉</span> Copy Blog"; }, 2500);
    })
    .catch(() => showToast("Copy failed. Please select and copy manually.", "error"));
});

downloadBtn.addEventListener("click", () => {
  if (!currentData?.final_blog) { showToast("No content to download", "error"); return; }
  const keyword = currentData.keyword || "blog";
  const filename = keyword.replace(/\s+/g, "-").toLowerCase() + ".md";
  const blob = new Blob([currentData.final_blog], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
  showToast("Downloading blog as .md file", "success");
});

// ─────────────────────────────────────────────
// RETRY
// ─────────────────────────────────────────────
retryBtn.addEventListener("click", () => {
  showSection(null);
  loadingSection.style.display  = "none";
  resultsSection.style.display  = "none";
  errorSection.style.display    = "none";
  keywordInput.focus();
});

// ─────────────────────────────────────────────
// EVENT LISTENERS
// ─────────────────────────────────────────────
generateBtn.addEventListener("click", generateBlog);
keywordInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") generateBlog();
});

// Auto-focus input on page load
keywordInput.focus();
