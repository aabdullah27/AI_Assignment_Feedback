import streamlit as st
import os
import tempfile
import time
import pymupdf4llm
import pandas as pd
import matplotlib.pyplot as plt
from google import genai
from dotenv import load_dotenv
from fpdf import FPDF
import plotly.express as px
import plotly.graph_objects as go
import re

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="AI PDF Feedback System",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 42px;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 20px;
        text-align: center;
    }
    .sub-header {
        font-size: 24px;
        font-weight: 600;
        color: #4B5563;
        margin-bottom: 10px;
    }
    .card {
        background-color: #F9FAFB;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    .score-card {
        text-align: center;
        background: linear-gradient(135deg, #a5b4fc 0%, #818cf8 100%);
        color: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .score-text {
        font-size: 48px;
        font-weight: bold;
    }
    .grade-text {
        font-size: 36px;
        font-weight: bold;
    }
    .feedback-section {
        background-color: #EFF6FF;
        border-left: 5px solid #3B82F6;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .improvement-item {
        background-color: #FEF2F2;
        border-left: 5px solid #EF4444;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .strength-item {
        background-color: #ECFDF5;
        border-left: 5px solid #10B981;
        padding: 15px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .stProgress > div > div > div > div {
        background-color: #6366F1;
    }
</style>
""", unsafe_allow_html=True)

# Function to initialize Gemini client
@st.cache_resource
def initialize_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)
    if not api_key:
        st.error("No Gemini API key found. Please set it in .env file or Streamlit secrets.")
        st.stop()
    return genai.Client(api_key=api_key)

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    try:
        with st.spinner("Extracting text from PDF..."):
            md_text = pymupdf4llm.to_markdown(file_path)
            return md_text
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

# Function to chunk text for long PDFs
def chunk_text(text, max_chunk_size=8000):
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0
    
    for word in words:
        if current_size + len(word) + 1 > max_chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_size = len(word)
        else:
            current_chunk.append(word)
            current_size += len(word) + 1  # +1 for the space
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

# Function to analyze PDF with Gemini
def analyze_pdf_with_gemini(client, text):
    try:
        with st.spinner("AI is analyzing your document..."):
            # For long documents, chunk and analyze separately
            if len(text) > 30000:
                st.info("Document is large. Processing in chunks...")
                chunks = chunk_text(text)
                summaries = []
                
                progress_bar = st.progress(0)
                for i, chunk in enumerate(chunks):
                    progress_bar.progress((i+1)/len(chunks))
                    
                    chunk_prompt = f"""
                    Analyze this portion of an academic paper or assignment:
                    
                    {chunk}
                    
                    Extract key points, strengths, and weaknesses from this section.
                    """
                    
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=chunk_prompt,
                    )
                    
                    summaries.append(response.text)
                
                combined_summary = "\n\n".join(summaries)
                
                # Final analysis of the combined summaries
                final_prompt = f"""
                You are an expert academic assessor. Below are summaries from different parts of a student assignment.
                
                {combined_summary}
                
                Based on these summaries, provide a comprehensive assessment in the following JSON format:
                
                ```json
                {{
                    "title": "Assessment Title",
                    "grade": "Letter grade (A+, A, A-, B+, etc.)",
                    "score": A number between 0 and 100,
                    "summary": "One paragraph summary of the work",
                    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
                    "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
                    "detailed_feedback": "Comprehensive feedback in 3-4 paragraphs",
                    "category_scores": {{
                        "Content": Score between 0 and 100,
                        "Structure": Score between 0 and 100,
                        "Analysis": Score between 0 and 100,
                        "Language": Score between 0 and 100,
                        "References": Score between 0 and 100
                    }}
                }}
                ```
                
                Ensure your assessment is fair, constructive, and specific to help the student improve.
                """
                
            else:
                # For shorter documents, analyze directly
                final_prompt = f"""
                You are an expert academic assessor. Carefully analyze this student assignment:
                
                {text}
                
                Provide a comprehensive assessment in the following JSON format:
                
                ```json
                {{
                    "title": "Assessment Title",
                    "grade": "Letter grade (A+, A, A-, B+, etc.)",
                    "score": A number between 0 and 100,
                    "summary": "One paragraph summary of the work",
                    "strengths": ["Strength 1", "Strength 2", "Strength 3"],
                    "areas_for_improvement": ["Area 1", "Area 2", "Area 3"],
                    "detailed_feedback": "Comprehensive feedback in 3-4 paragraphs",
                    "category_scores": {{
                        "Content": Score between 0 and 100,
                        "Structure": Score between 0 and 100,
                        "Analysis": Score between 0 and 100,
                        "Language": Score between 0 and 100,
                        "References": Score between 0 and 100
                    }}
                }}
                ```
                
                Ensure your assessment is fair, constructive, and specific to help the student improve.
                """
            
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=final_prompt,
            )   
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_string = json_match.group(1)
            else:
                json_string = response.text
            
            import json
            try:
                result = json.loads(json_string)
                return result
            except json.JSONDecodeError:
                st.error("Error parsing AI response. Please try again.")
                st.code(response.text)
                return None
                
    except Exception as e:
        st.error(f"Error analyzing PDF: {e}")
        return None

# Function to create feedback PDF
def create_feedback_pdf(feedback_data):
    pdf = FPDF()
    pdf.add_page()
    
    # Set font
    pdf.set_font("Arial", "B", 16)
    
    # Title
    pdf.cell(0, 10, "Assignment Feedback Report", 0, 1, "C")
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    
    # Basic info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, f"Title: {feedback_data['title']}", 0, 1)
    pdf.cell(0, 10, f"Grade: {feedback_data['grade']} ({feedback_data['score']}/100)", 0, 1)
    pdf.ln(5)
    
    # Summary
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Summary:", 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 10, feedback_data['summary'])
    pdf.ln(5)
    
    # Strengths
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Strengths:", 0, 1)
    pdf.set_font("Arial", "", 10)
    for strength in feedback_data['strengths']:
        pdf.cell(0, 10, f"• {strength}", 0, 1)
    pdf.ln(5)
    
    # Areas for improvement
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Areas for Improvement:", 0, 1)
    pdf.set_font("Arial", "", 10)
    for area in feedback_data['areas_for_improvement']:
        pdf.cell(0, 10, f"• {area}", 0, 1)
    pdf.ln(5)
    
    # Category scores
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Category Scores:", 0, 1)
    pdf.set_font("Arial", "", 10)
    for category, score in feedback_data['category_scores'].items():
        pdf.cell(0, 10, f"{category}: {score}/100", 0, 1)
    pdf.ln(5)
    
    # Detailed feedback
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Detailed Feedback:", 0, 1)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 10, feedback_data['detailed_feedback'])
    
    # Generate PDF file in memory
    return pdf.output(dest="S").encode("latin1")

# Function to create markdown report
def create_markdown_report(feedback_data):
    md = f"""# Assignment Feedback Report

## {feedback_data['title']}

**Grade: {feedback_data['grade']} ({feedback_data['score']}/100)**

### Summary
{feedback_data['summary']}

### Strengths
{"".join(['- ' + strength + '\n' for strength in feedback_data['strengths']])}

### Areas for Improvement
{"".join(['- ' + area + '\n' for area in feedback_data['areas_for_improvement']])}

### Category Scores
{"".join(['- ' + category + ': ' + str(score) + '/100\n' for category, score in feedback_data['category_scores'].items()])}

### Detailed Feedback
{feedback_data['detailed_feedback']}
"""
    return md

# Main application
def main():
    st.markdown('<div class="main-header">AI PDF Feedback System</div>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = None
    if 'pdf_text' not in st.session_state:
        st.session_state.pdf_text = None
    
    # Sidebar
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Plus_symbol.svg/1200px-Plus_symbol.svg.png", width=50)
        st.markdown("### Upload Assignment")
        
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
        
        if uploaded_file is not None:
            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            # Extract text from PDF
            st.session_state.pdf_text = extract_text_from_pdf(tmp_path)
            
            if st.session_state.pdf_text:
                st.success("PDF uploaded and text extracted successfully!")
                
                # Display PDF info
                st.markdown("### PDF Information")
                word_count = len(st.session_state.pdf_text.split())
                st.info(f"Word count: {word_count}")
                
                # Analyze button
                if st.button("Analyze Assignment", type="primary"):
                    # Initialize Gemini client
                    client = initialize_gemini_client()
                    
                    # Analyze PDF
                    st.session_state.feedback_data = analyze_pdf_with_gemini(client, st.session_state.pdf_text)
            
            # Clean up temporary file
            os.unlink(tmp_path)
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("""
        This AI-powered system analyzes academic assignments and provides comprehensive feedback including grading, strengths, and areas for improvement.
        
        Upload your PDF document and get instant, detailed feedback.
        """)
    
    # Main content
    if st.session_state.feedback_data:
        feedback_data = st.session_state.feedback_data
        
        # Title and Grade Display
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"<div class='card'><div class='sub-header'>{feedback_data['title']}</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class='score-card'>
                <div class='grade-text'>{feedback_data['grade']}</div>
                <div class='score-text'>{feedback_data['score']}/100</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Category Scores with Charts
        st.markdown("<div class='sub-header'>Category Scores</div>", unsafe_allow_html=True)
        
        # Prepare data for chart
        categories = list(feedback_data['category_scores'].keys())
        scores = list(feedback_data['category_scores'].values())
        
        # Create radar chart with Plotly
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=categories,
            fill='toself',
            name='Assignment Score',
            line_color='#6366F1',
            fillcolor='rgba(99, 102, 241, 0.3)'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=False,
            height=400,
            margin=dict(l=80, r=80, t=20, b=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Create bar chart for category scores
        fig_bar = px.bar(
            x=categories,
            y=scores,
            labels={'x': 'Category', 'y': 'Score'},
            color=scores,
            color_continuous_scale='Blues',
            range_y=[0, 100]
        )
        fig_bar.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20),
            coloraxis_showscale=False
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Summary
        st.markdown("<div class='sub-header'>Summary</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='feedback-section'>{feedback_data['summary']}</div>", unsafe_allow_html=True)
        
        # Strengths and Areas for Improvement
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='sub-header'>Strengths</div>", unsafe_allow_html=True)
            for strength in feedback_data['strengths']:
                st.markdown(f"<div class='strength-item'>{strength}</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='sub-header'>Areas for Improvement</div>", unsafe_allow_html=True)
            for area in feedback_data['areas_for_improvement']:
                st.markdown(f"<div class='improvement-item'>{area}</div>", unsafe_allow_html=True)
        
        # Detailed Feedback
        st.markdown("<div class='sub-header'>Detailed Feedback</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='feedback-section'>{feedback_data['detailed_feedback']}</div>", unsafe_allow_html=True)
        
        # Download options
        st.markdown("<div class='sub-header'>Download Report</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            pdf_bytes = create_feedback_pdf(feedback_data)
            st.download_button(
                label="Download as PDF",
                data=pdf_bytes,
                file_name="assignment_feedback.pdf",
                mime="application/pdf"
            )
        
        with col2:
            md_content = create_markdown_report(feedback_data)
            st.download_button(
                label="Download as Markdown",
                data=md_content,
                file_name="assignment_feedback.md",
                mime="text/markdown"
            )
    
    else:
        # Display welcome message and instructions
        st.markdown("""
        <div class='card'>
            <h2>Welcome to the AI PDF Feedback System</h2>
            <p>This system uses advanced AI to analyze academic assignments and provide comprehensive feedback.</p>
            <p>To get started:</p>
            <ol>
                <li>Upload your assignment PDF using the sidebar on the left</li>
                <li>Click "Analyze Assignment" to generate feedback</li>
                <li>Review your detailed assessment with scores, strengths, and improvement areas</li>
                <li>Download your feedback report in PDF or Markdown format</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
if __name__ == "__main__":
    main()