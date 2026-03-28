<h1 align="center">📄 AI-Powered Resume Analyzer</h1>

<p align="center">
  <strong>A fast & intelligent resume screening tool built with Streamlit and Google Gemini 2.5 Flash.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/Streamlit-1.44.1-FF4B4B.svg" alt="Streamlit">
  <img src="https://img.shields.io/badge/AI-Google_Gemini-orange.svg" alt="Gemini">
</p>

---

## 🌟 Key Features

* 📊 **Visual Scoring & Analytics:** Immediately compare candidates against job descriptions with a 0-100% **Overall ATS Match** and a beautiful, interactive **Skills Radar Chart** (built with Plotly) breaking down Technical, Leadership, and Communication competencies.
* 🔑 **Keyword Extraction:** Distinctly lists exactly which crucial ATS keywords from the Job Description the candidate successfully hit (**✅ Found**) and which ones they are missing (**❌ Missing**).
* 💬 **"Chat with the Resume":** An interactive Q&A feature explicitly built into the dashboard. Ask the AI follow-up questions like *"Did they mention leading any teams?"* and it will read directly from the cached resume text.
* 📥 **One-Click PDF Export:** Instantly compile the candidate's scores, strengths, and weaknesses into a cleanly formatted, offline-ready PDF report (using `fpdf2`).
* 🔒 **Secure Local Processing:** No exposed API keys in the UI. Keep your Google credentials wrapped securely inside your local environment variables.

## 🛠️ Installation & Setup

**1. Clone the repository and navigate inside:**
```bash
git clone https://github.com/nikhilagrawal-dev/AI-RESUME-ANALYZER-.git
cd AI-RESUME-ANALYZER-
```

**2. Install the necessary dependencies:**
```bash
pip install -r requirements.txt
```

**3. Configure your Google Gemini API Key:**
* Create a `.env` file in the root directory.
* Add your key exactly like this:
```txt
GEMINI_API_KEY="AIza_YOUR_ACTUAL_KEY_HERE"
```
*(Generate a free API key at [Google AI Studio](https://aistudio.google.com/app/apikey))*

**4. Run the Streamlit Application:**
```bash
streamlit run app.py
```

## 💻 Tech Stack
* **Frontend/UI:** Streamlit, Plotly (`px.line_polar`)
* **AI/LLM:** Google Generative AI SDK (`gemini-2.5-flash`)
* **File Processing:** `PyMuPDF` (PDFs), `python-docx` (Documents)
* **Utilities:** `pandas`, `fpdf2`, `python-dotenv`
