# AI Blog Engine — Multi-Agent System

A production-ready, hackathon-winning AI-powered blog generation system using a 7-agent pipeline.

## ⚡ Quick Setup (5 minutes)

### 1. Get a FREE Gemini API Key
1. Go to: https://aistudio.google.com/app/apikey
2. Click **"Create API key"**
3. Copy your key

### 2. Install Dependencies
```bash
pip install flask google-generativeai
```

### 3. Set Your API Key

**Option A — Environment variable (recommended):**
```bash
# macOS / Linux
export GEMINI_API_KEY="your-key-here"

# Windows CMD
set GEMINI_API_KEY=your-key-here

# Windows PowerShell
$env:GEMINI_API_KEY="your-key-here"
```

**Option B — Edit app.py directly:**
```python
GEMINI_API_KEY = "your-key-here"  # line ~15 in app.py
```

### 4. Run the App
```bash
cd ai_blog_engine
python app.py
```

### 5. Open in Browser
```
http://localhost:5000
```

---

## 📁 Project Structure

```
ai_blog_engine/
├── app.py                  # Flask backend + 7 AI agents
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── templates/
│   └── index.html          # Frontend HTML
└── static/
    ├── style.css           # Dark/light theme CSS
    └── script.js           # Frontend logic
```

---

## 🤖 The 7-Agent Pipeline

| Agent | Role |
|-------|------|
| 01 - Intent Analyzer | Classifies keyword as informational/commercial/transactional |
| 02 - Keyword Clustering | Primary, secondary, long-tail, LSI, and question keywords |
| 03 - SERP Gap Analysis | Identifies content gaps vs. competitors |
| 04 - Outline Generator | SEO-optimized H1/H2/H3 structure |
| 05 - Blog Generator | Full 1500-2000 word blog post |
| 06 - SEO Optimizer | Score out of 100 with recommendations |
| 07 - Humanizer | Removes AI patterns, adds personality |

---

## ✨ Features

- 🎨 **Dark/Light theme** — toggle in header
- 📊 **SEO score** — out of 100 with grade (A/B/C/D)
- 📝 **Word count** + read time estimate
- 📋 **Copy to clipboard** — one-click copy
- 💾 **Download as .md** — save locally
- 📑 **Tabbed interface** — organized results
- 🔄 **Loading animation** — real-time agent progress

---

## 🆓 Free API Limits (Gemini 1.5 Flash)

- 15 requests per minute
- 1,000,000 tokens per minute  
- 1,500 requests per day

This is more than enough for development and hackathon use.

---

## 🚀 Deploy to Production

```bash
# Install gunicorn
pip install gunicorn

# Run production server
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```
