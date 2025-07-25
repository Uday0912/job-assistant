# app.py
import json
import PyPDF2
import docx
import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import spacy
import plotly.express as px
from transformers import pipeline
import subprocess

# Ensure spaCy model is available
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"], check=True)
    nlp = spacy.load("en_core_web_sm")

st.set_page_config(page_title="Job Application Assistant - Enhanced", layout="wide")

@st.cache_resource
def load_models():
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    text_gen = pipeline("text-generation", model="gpt2")
    return summarizer, text_gen

summarizer, text_gen = load_models()

def read_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([p.text for p in doc.paragraphs])

def load_resume(uploaded_file):
    if uploaded_file.name.endswith('.pdf'):
        return read_pdf(uploaded_file)
    elif uploaded_file.name.endswith('.docx'):
        return read_docx(uploaded_file)
    else:
        st.error("Unsupported file format")
        return None

def generate_updated_resume(resume_text):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        name='NormalText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    content = [Paragraph("Updated Resume", styles['Heading1']), Spacer(1, 12)]
    content += [Paragraph(line.strip(), normal_style) for line in resume_text.split("\n") if line.strip()]
    doc.build(content)
    buffer.seek(0)
    return buffer

def analyze_text(text):
    text = text[:1500]
    summary = summarizer(text, max_length=200, min_length=50, do_sample=False, truncation=True)[0]['summary_text']
    return summary

def generate_cover_letter(summary, tone="friendly"):
    prompts = {
        "friendly": "Write a friendly and positive cover letter",
        "professional": "Write a professional and formal cover letter",
        "informal": "Write a casual and informal cover letter"
    }
    prompt = f"{prompts[tone]} based on the following summary: {summary[:700]}"
    return text_gen(prompt, max_new_tokens=200, num_return_sequences=1)[0]['generated_text']

def extract_skills(text):
    doc = nlp(text)
    return set(chunk.text.strip().lower() for chunk in doc.noun_chunks if 3 < len(chunk.text) < 30 and chunk.text[0].isalpha())

def skill_comparison_chart(matched, missing, extra):
    data = {
        "Skill Type": ["Matched"]*len(matched) + ["Missing"]*len(missing) + ["Extra"]*len(extra),
        "Skill": list(matched) + list(missing) + list(extra)
    }
    df = pd.DataFrame(data)
    if not df.empty:
        fig = px.bar(df, x="Skill", color="Skill Type", title="Skill Comparison", barmode="group", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No skills found to compare.")

def show_ats_suggestions():
    st.markdown("### 🔍 ATS Suggestions")
    st.info("""
- Use standard section titles: Experience, Education, Skills
- Stick to common fonts (Arial, Calibri, Times New Roman)
- Include measurable achievements (e.g., "Improved efficiency by 25%")
- Avoid using graphics, tables, or columns
- Use bullet points instead of paragraphs for readability
""")

def main():
    st.title("Job Application Assistant")
    st.markdown("Analyze your resume & job description, generate a cover letter, and download an updated resume – all for free!")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Job Description 📋")
        job_desc = st.text_area("Paste the job description here", height=300)
    with col2:
        st.subheader("Your Resume 📜")
        resume_file = st.file_uploader("Upload your resume", type=['pdf', 'docx'])

    if job_desc and resume_file:
        with st.spinner("🔍 Analyzing your application..."):
            resume_text = load_resume(resume_file)
            if resume_text:
                job_summary = analyze_text(job_desc)
                resume_summary = analyze_text(resume_text)

                st.header("Analysis Results 📊")
                st.subheader("Job Summary")
                st.info(job_summary)
                st.subheader("Resume Summary")
                st.info(resume_summary)

                job_skills = extract_skills(job_desc)
                resume_skills = extract_skills(resume_text)
                matched_skills = job_skills & resume_skills
                missing_skills = job_skills - resume_skills
                extra_skills = resume_skills - job_skills

                st.header("Skill Comparison 🔍")
                st.markdown("#### ✅ Matched Skills")
                st.write(", ".join(sorted(matched_skills)) or "None found")
                st.markdown("#### ❌ Skills You Need to Learn")
                st.write(", ".join(sorted(missing_skills)) or "You're all set!")
                st.markdown("#### 🎁 Top 10 Extra Skills You Have")
                top_extra = sorted(extra_skills, key=lambda s: (-len(s), s))[:10]
                st.write(", ".join(top_extra) or "None")

                skill_comparison_chart(matched_skills, missing_skills, top_extra)
                show_ats_suggestions()

                st.header("Cover Letter 💌")
                tone = st.selectbox("Choose Cover Letter Tone", ["friendly", "professional", "informal"])
                if st.button("Generate Cover Letter ✨"):
                    with st.spinner("Generating cover letter..."):
                        try:
                            full_summary = job_summary + " " + resume_summary
                            letter = generate_cover_letter(full_summary, tone)
                            formatted = f"Dear Hiring Manager,\n\n{letter.strip()}\n\nSincerely,\nParsha Uday"
                            st.text_area("Your Generated Cover Letter", formatted, height=400)
                            st.download_button("Download Cover Letter 📥", formatted, "cover_letter.txt", "text/plain")
                        except Exception as e:
                            st.error(f"Error: {e}")

                st.header("Updated Resume 📝")
                updated_resume = generate_updated_resume(resume_text)
                st.download_button("Download Updated Resume 📥", updated_resume, "updated_resume.pdf", mime="application/pdf")

if __name__ == "__main__":
    main()
