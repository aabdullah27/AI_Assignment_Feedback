import streamlit as st
import os
import tempfile
import time
import pymupdf4llm
import pandas as pd
import matplotlib.pyplot as plt
from google import genai
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go
import re
import io
import json

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="AI PDF Feedback System",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
                        contents=chunk_prompt
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
                contents=final_prompt
            )
            
            # Extract JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response.text, re.DOTALL)
            if json_match:
                json_string = json_match.group(1)
            else:
                json_string = response.text
            
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
    st.title("AI PDF Feedback System")
    
    # Initialize session state
    if 'feedback_data' not in st.session_state:
        st.session_state.feedback_data = None
    if 'pdf_text' not in st.session_state:
        st.session_state.pdf_text = None
    
    # Sidebar
    with st.sidebar:
        st.header("Upload Assignment")
        
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
                st.subheader("PDF Information")
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
        
        st.divider()
        st.subheader("About")
        st.write("""
        This AI-powered system analyzes academic assignments and provides comprehensive feedback including grading, strengths, and areas for improvement.
        
        Upload your PDF document and get instant, detailed feedback.
        """)
    
    # Main content
    if st.session_state.feedback_data:
        feedback_data = st.session_state.feedback_data
        
        # Title and Grade Display
        col1, col2 = st.columns(2)
        with col1:
            st.subheader(feedback_data['title'])
        with col2:
            st.metric(label="Grade", value=feedback_data['grade'], delta=f"{feedback_data['score']}/100")
        
        # Category Scores with Charts
        st.subheader("Category Scores")
        
        # Prepare data for chart
        categories = list(feedback_data['category_scores'].keys())
        scores = list(feedback_data['category_scores'].values())
        
        # Create radar chart with Plotly
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=scores,
            theta=categories,
            fill='toself',
            name='Assignment Score'
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
            range_y=[0, 100]
        )
        fig_bar.update_layout(
            height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Summary
        st.subheader("Summary")
        st.info(feedback_data['summary'])
        
        # Strengths and Areas for Improvement
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Strengths")
            for strength in feedback_data['strengths']:
                st.success(strength)
        
        with col2:
            st.subheader("Areas for Improvement")
            for area in feedback_data['areas_for_improvement']:
                st.warning(area)
        
        # Detailed Feedback
        st.subheader("Detailed Feedback")
        st.write(feedback_data['detailed_feedback'])
        
        # Download options
        st.subheader("Download Report")
        
        md_content = create_markdown_report(feedback_data)
        st.download_button(
            label="Download as Markdown",
            data=md_content,
            file_name="assignment_feedback.md",
            mime="text/markdown"
        )
    
    else:
        # Display welcome message and instructions
        st.header("📄 Welcome to the AI PDF Feedback System!")
        st.write("""
        🧠 This tool uses AI to analyze your academic assignments and give smart, actionable feedback.

        **Get Started in 4 Easy Steps:**
        
        1️⃣ Upload your assignment PDF from the sidebar  
        2️⃣ Click **Analyze Assignment**  
        3️⃣ Get detailed scores, strengths & improvement tips  
        4️⃣ Download your feedback in 📄 Markdown format
        """)

        # Sample columns layout
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📤 Step 1")
            st.write("Upload your assignment PDF")
        with col2:
            st.subheader("⚙️ Step 2")
            st.write("Click to analyze & receive AI feedback")

if __name__ == "__main__":
    main()