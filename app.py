import streamlit as st
import fitz  # PyMuPDF
import docx
import os
import json
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import google.generativeai as genai
from dotenv import load_dotenv
import ai_optimizer

load_dotenv() # Load variables from .env file

import string

def sanitize_for_pdf(text):
    if not text: return ""
    text = str(text)
    replacements = {
        '“': '"', '”': '"', "‘": "'", "’": "'",
        '–': '-', '—': '-', '…': '...',
        '•': '-', '●': '-', '★': '*', '☆': '*',
        '\t': ' ', '\r': '', '\n': ' '
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    
    # Strictly keep only printable ascii
    valid_chars = set(string.printable)
    text = ''.join(c for c in text if c in valid_chars)
    
    # Limit maximum word length to avoid fpdf horizontal space exceptions
    words = text.split()
    safe_words = [w[:90] for w in words] 
    return " ".join(safe_words)

def create_pdf_report(analysis_dict):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    pdf.set_x(10)
    pdf.cell(0, 10, "Resume Analysis Report", align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.set_x(10)
    pdf.cell(0, 10, f"ATS Match: {analysis_dict.get('ats_match_percentage', 0)}%")
    pdf.ln(10)
    
    assessment = sanitize_for_pdf(analysis_dict.get('assessment', ''))
    pdf.set_x(10)
    pdf.multi_cell(0, 10, f"Assessment: {assessment}")
    
    pdf.set_x(10)
    pdf.cell(0, 10, "Strengths:")
    pdf.ln(10)
    for s in analysis_dict.get('strengths', []):
        pdf.set_x(10)
        pdf.multi_cell(0, 10, f"- {sanitize_for_pdf(s)}")
        
    pdf.set_x(10)
    pdf.cell(0, 10, "Weaknesses:")
    pdf.ln(10)
    for w in analysis_dict.get('weaknesses', []):
        pdf.set_x(10)
        pdf.multi_cell(0, 10, f"- {sanitize_for_pdf(w)}")
        
    out = pdf.output()
    return bytes(out) if not isinstance(out, bytes) else out

# --- Configure API Key ---
api_key = os.environ.get("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)

# --- File Readers ---
def read_pdf(file):
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def extract_text(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        return read_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".docx"):
        return read_docx(uploaded_file)
    else:
        return "Unsupported file format. Please upload a .pdf or .docx file."

# --- Google Generative AI Call ---
def get_job_recommendations(resume_text):
    prompt = f"""
    You are a career advisor. Based on the following resume, suggest 3 to 5 job roles that best match this candidate's skills and experience.
    Resume:
    {resume_text}

    Return ONLY a valid JSON array (no markdown, no backticks) of objects with these exact keys:
    [
      {{
        "title": "<job title>",
        "why_it_fits": "<1-2 sentence explanation>",
        "where_to_apply": "<suggested platforms or company types e.g. LinkedIn, startups, FAANG>"
      }}
    ]
    """
    model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        raise e

def get_improvement_tips(resume_text, job_description):
    prompt = f"""
    You are an expert resume coach. Analyze the resume below and give specific, actionable improvement advice.
    Resume:
    {resume_text}
    Job Description:
    {job_description}

    Return ONLY a valid JSON object (no markdown, no backticks) with these exact keys:
    {{
      "bullet_rewrites": ["<original bullet> → <improved version>"],
      "skills_to_add": ["skill or certification to pursue"],
      "formatting_tips": ["formatting or structure tip"]
    }}
    """
    model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        raise e

def analyze_resume(resume_text, job_description):
    prompt = f"""
    You are a resume evaluation expert. Analyze the following resume:
    {resume_text}
    in the context of this job description:
    {job_description}
    
    Return ONLY a valid JSON object (no markdown formatting, no backticks) with the following exact keys:
    {{
      "ats_match_percentage": <int 0-100 indicating overall alignment>,
      "technical_score": <int 0-100>,
      "leadership_score": <int 0-100>,
      "communication_score": <int 0-100>,
      "found_keywords": ["keyword1", "keyword2"],
      "missing_keywords": ["keyword1", "keyword2"],
      "assessment": "<short overall assessment string>",
      "strengths": ["strength1", "strength2"],
      "weaknesses": ["weakness1", "weakness2"],
      "actionable_suggestions": ["suggestion1"]
    }}
    """

    generation_config = {"response_mime_type": "application/json"}
    model = genai.GenerativeModel("gemini-2.5-flash", generation_config=generation_config)
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        if "404" in str(e):
            models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            raise Exception(f"Model not found. Available models for your API key: {', '.join(models)}")
        raise e

# --- Streamlit UI ---
st.set_page_config(page_title="AI Resume Analyzer", layout="wide")
st.title("📄 AI-Powered Resume Analyzer")

with st.sidebar:
    st.header("Upload Files")
    resume_file = st.file_uploader("Upload Resume (.pdf or .docx)", type=["pdf", "docx"])
    jd_file = st.file_uploader("Upload Job Description (.pdf or .docx)", type=["pdf", "docx"])

analyze_button = st.button("🔍 Analyze Resume")

if analyze_button and resume_file and jd_file:
    api_key_val = api_key and api_key.strip()
    if not api_key_val:
        st.error("⚠️ The GEMINI_API_KEY environment variable is not set. Please restart the app with this variable set.")
    elif not api_key_val.startswith("AIza"):
        st.error("⚠️ The GEMINI_API_KEY environment variable doesn't look like a valid Google Gemini key (it should start with 'AIza').")
    else:
        with st.spinner("Extracting text and analyzing..."):
            try:
                resume_text = extract_text(resume_file)
                job_text = extract_text(jd_file)
                
                # Cache for chat
                st.session_state.resume_text_cache = resume_text
                st.session_state.job_text_cache = job_text
                
                analysis = analyze_resume(resume_text, job_text)
                st.session_state.last_analysis = analysis
            except Exception as e:
                st.error(f"⚠️ {str(e)}")

elif analyze_button:
    st.warning("Please upload both resume and job description to proceed.")

# --- Display Results & Chat ---
if "last_analysis" in st.session_state:
    analysis = st.session_state.last_analysis
    st.success(f"### Overall ATS Match: {analysis.get('ats_match_percentage', 0)}%")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Skills Breakdown")
        df = pd.DataFrame(dict(
            r=[analysis.get('technical_score', 0), analysis.get('leadership_score', 0), analysis.get('communication_score', 0)],
            theta=['Technical', 'Leadership', 'Communication']
        ))
        fig = px.line_polar(df, r='r', theta='theta', line_close=True)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("🔑 ATS Keywords")
        st.write("**✅ Found:** " + ", ".join(analysis.get('found_keywords', [])))
        st.write("**❌ Missing:** " + ", ".join(analysis.get('missing_keywords', [])))

    st.subheader("📝 Summary")
    st.write(analysis.get('assessment', ''))
    
    st.markdown("### 🌟 Strengths")
    for s in analysis.get('strengths', []):
        st.write(f"- {s}")
        
    st.markdown("### ⚠️ Weaknesses")
    for w in analysis.get('weaknesses', []):
        st.write(f"- {w}")

    # --- Job Role Recommendations ---
    st.markdown("---")
    st.subheader("💼 Job Role Recommendations")
    if "job_recommendations" not in st.session_state:
        if st.button("🔍 Get Job Recommendations"):
            with st.spinner("Finding best-matching roles..."):
                try:
                    recs = get_job_recommendations(st.session_state.resume_text_cache)
                    st.session_state.job_recommendations = recs
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        for rec in st.session_state.job_recommendations:
            with st.expander(f"🏷️ {rec.get('title', 'Role')}"):
                st.write(f"**Why it fits:** {rec.get('why_it_fits', '')}")
                st.write(f"**Where to apply:** {rec.get('where_to_apply', '')}")
        if st.button("🔄 Refresh Recommendations"):
            del st.session_state.job_recommendations
            st.rerun()

    # --- Resume Improvement Coach ---
    st.markdown("---")
    st.subheader("🛠️ Resume Improvement Coach")
    if "improvement_tips" not in st.session_state:
        if st.button("💡 Get Improvement Tips"):
            with st.spinner("Analyzing and generating tips..."):
                try:
                    tips = get_improvement_tips(
                        st.session_state.resume_text_cache,
                        st.session_state.job_text_cache
                    )
                    st.session_state.improvement_tips = tips
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        tips = st.session_state.improvement_tips
        st.markdown("**✏️ Bullet Point Rewrites:**")
        for b in tips.get("bullet_rewrites", []):
            st.write(f"- {b}")
        st.markdown("**📚 Skills & Certifications to Add:**")
        for s in tips.get("skills_to_add", []):
            st.write(f"- {s}")
        st.markdown("**📐 Formatting & Structure Tips:**")
        for f in tips.get("formatting_tips", []):
            st.write(f"- {f}")
        if st.button("🔄 Refresh Tips"):
            del st.session_state.improvement_tips
            st.rerun()

    pdf_bytes = create_pdf_report(analysis)
    st.download_button(label="📥 Export to PDF", data=pdf_bytes, file_name="resume_analysis.pdf", mime="application/pdf")

    # --- Resume Score Optimizer (Hill Climbing) ---
    st.markdown("---")
    st.subheader("🚀 Resume Score Optimizer (Hill Climbing)")
    st.info("Improve your ATS score by iteratively adding high-impact keywords and replacing weak ones.")
    
    if st.button("📈 Optimize Resume Score"):
        with st.spinner("Running Hill Climbing Optimization..."):
            try:
                found = analysis.get('found_keywords', [])
                missing = analysis.get('missing_keywords', [])
                jd_text = st.session_state.job_text_cache
                
                results = ai_optimizer.hill_climbing_optimize(found, missing, jd_text)
                st.session_state.optimization_results = results
                st.rerun()
            except Exception as e:
                st.error(f"Optimization Error: {e}")
                
    if "optimization_results" in st.session_state:
        res = st.session_state.optimization_results
        
        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            st.metric("Original Score", f"{res['original_score']}%")
        with col_opt2:
            st.metric("Optimized Score", f"{res['optimized_score']}%", delta=f"{res['optimized_score'] - res['original_score']}%")
            
        st.markdown("### 🛠️ Suggested Improvements")
        
        c1, c2 = st.columns(2)
        with c1:
            if res['added']:
                st.success("**✅ Keywords to Add:**\n\n" + ", ".join(res['added']))
        with c2:
            if res['removed']:
                st.warning("**❌ Keywords to Replace:**\n\n" + ", ".join(res['removed']))
                
        with st.expander("📝 Step-by-Step Optimization History"):
            for step in res['history']:
                st.write(f"- {step}")
                
        if st.button("🔄 Reset Optimization"):
            del st.session_state.optimization_results
            st.rerun()

    st.markdown("---")
    st.subheader("💬 Chat with this Resume")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        
    for msg in st.session_state.chat_history:
        st.chat_message(msg["role"]).write(msg["text"])
        
    if user_q := st.chat_input("Ask a question about this resume..."):
        st.chat_message("user").write(user_q)
        st.session_state.chat_history.append({"role": "user", "text": user_q})
        
        qa_prompt = f"Resume:\n{st.session_state.resume_text_cache}\n\nQuestion: {user_q}"
        qa_model = genai.GenerativeModel("gemini-2.5-flash")
        try:
            answer_obj = qa_model.generate_content(qa_prompt)
            st.chat_message("assistant").write(answer_obj.text)
            st.session_state.chat_history.append({"role": "assistant", "text": answer_obj.text})
        except Exception as e:
            st.error(f"Chat Error: {e}")


