import json
import PyPDF2
import docx
import streamlit as st
import pandas as pd
import re
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import plotly.express as px
from transformers import pipeline

# ✅ Streamlit page config
st.set_page_config(page_title="Job Application Assistant", layout="wide")

# ✅ Cache model loading
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
        if page.extract_text():
            text += page.extract_text()
    return text

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

def load_resume(uploaded_file):
    if uploaded_file.name.endswith('.pdf'):
        return read_pdf(uploaded_file)
    elif uploaded_file.name.endswith('.docx'):
        return read_docx(uploaded_file)
    else:
        st.error("Unsupported file format")
        return ""

def generate_updated_resume(resume_text):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    h1 = styles['Heading1']
    normal = ParagraphStyle(name='NormalText', parent=styles['Normal'], fontSize=10, leading=14)
    flow = [Paragraph("Updated Resume", h1), Spacer(1,12)]
    for line in resume_text.split("\n"):
        if line.strip():
            flow.append(Paragraph(line.strip(), normal))
    doc.build(flow)
    buffer.seek(0)
    return buffer

def analyze_text(text):
    text = text[:1500]
    return summarizer(text, max_length=200, min_length=50, do_sample=False, truncation=True)[0]['summary_text']

def generate_cover_letter(summary, tone="friendly"):
    prompts = {
        "friendly": "Write a friendly and positive cover letter",
        "professional": "Write a professional and formal cover letter",
        "informal": "Write a casual and informal cover letter"
    }
    prompt = f"{prompts[tone]} based on: {summary[:700]}"
    return text_gen(prompt, max_new_tokens=200, num_return_sequences=1)[0]['generated_text']

# Simple skill extractor via regex for noun-like phrases
def extract_skills(text):
    # matches phrases of 1-3 words starting with capital or lowercase letter
    candidates = re.findall(r"\b[A-Za-z]{3,}(?:\s[A-Za-z]{3,}){0,2}\b", text)
    cleaned = set(phrase.lower() for phrase in candidates if len(phrase)>3)
    return cleaned

def skill_comparison_chart(m,mi,e):
    df = pd.DataFrame({
        "Skill Type": ["Matched"]*len(m)+["Missing"]*len(mi)+["Extra"]*len(e),
        "Skill": list(m)+list(mi)+list(e)
    })
    if not df.empty:
        fig = px.bar(df, x="Skill", color="Skill Type", barmode="group", title="Skill Comparison")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No skills to compare.")

def show_ats_suggestions():
    st.markdown("### 🔍 ATS Tips")
    st.info("""
- Use clear headings: Experience, Education, Skills  
- Choose standard fonts (Arial, Calibri)  
- Quantify achievements (e.g., Increased sales by 20%)  
- Avoid images/tables; use bullet points  
""")

def main():
    st.title("Job Application Assistant")
    st.markdown("Analyze resume & job description, generate cover letter, download updated resume.")

    c1, c2 = st.columns(2)
    with c1:
        jd = st.text_area("Job Description", height=250)
    with c2:
        rf = st.file_uploader("Your Resume", type=['pdf','docx'])

    if jd and rf:
        text = load_resume(rf)
        summary_jd = analyze_text(jd)
        summary_res = analyze_text(text)
        st.header("Summaries")
        st.subheader("JD") ; st.info(summary_jd)
        st.subheader("Resume") ; st.info(summary_res)

        skills_jd = extract_skills(jd)
        skills_res = extract_skills(text)
        m = skills_jd & skills_res
        mi = skills_jd - skills_res
        e = skills_res - skills_jd

        st.header("Skills")
        st.markdown("**Matched:** " + (", ".join(sorted(m)) or "None"))
        st.markdown("**Missing:** " + (", ".join(sorted(mi)) or "None"))
        st.markdown("**Extra:** " + (", ".join(sorted(e)) or "None"))
        skill_comparison_chart(m,mi,e)
        show_ats_suggestions()

        st.header("Cover Letter")
        tone = st.selectbox("Tone", ["friendly","professional","informal"])
        if st.button("Generate"):
            cl = generate_cover_letter(summary_jd + " " + summary_res, tone)
            letter = f"Dear Hiring Manager,\n\n{cl.strip()}\n\nSincerely,\nYour Name"
            st.text_area("Cover Letter", letter, height=300)
            st.download_button("Download Letter", letter, "cover_letter.txt")

        st.header("Download Updated Resume")
        buff = generate_updated_resume(text)
        st.download_button("Download PDF", buff, "updated_resume.pdf", "application/pdf")

if __name__=="__main__":
    main()
