import streamlit as st
import os
import tempfile
import time
import pymupdf4llm
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import re
import io
import json
import pathlib
import httpx
from google import genai
from dotenv import load_dotenv

# Import prompts from separate file
from assets.prompt import (
    LONG_CHUNK_ANALYSIS_PROMPT, 
    SHORT_DOCUMENT_ANALYSIS_PROMPT,
    FINAL_ASSESSMENT_PROMPT,
    FILE_API_ANALYSIS_PROMPT
)

# Load environment variables
load_dotenv()

class PDFProcessor:
    """Handles all PDF processing functionality"""
    
    @staticmethod
    def extract_text_from_pdf(file_path):
        """Extract text from PDF using pymupdf4llm"""
        try:
            md_text = pymupdf4llm.to_markdown(file_path)
            return md_text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {e}")
            return None
    
    @staticmethod
    def chunk_text(text, max_chunk_size=8000):
        """Split text into manageable chunks for processing"""
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


class GeminiProcessor:
    """Handles all Gemini AI processing"""
    
    def __init__(self):
        """Initialize Gemini client"""
        self.client = self._initialize_client()
        
    def _initialize_client(self):
        """Initialize and return Gemini client"""
        api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", None)
        if not api_key:
            st.error("No Gemini API key found. Please set it in .env file or Streamlit secrets.")
            st.stop()
        return genai.Client(api_key=api_key)
    
    def analyze_with_extracted_text(self, assignment_text, requirements_text=None):
        """Analyze PDF with Gemini using extracted text"""
        try:
            with st.spinner("Analyzing", show_time=True):
                # For long documents, chunk and analyze separately
                if len(assignment_text) > 30000:
                    return self._analyze_long_document(assignment_text, requirements_text)
                else:
                    # For shorter documents, analyze directly
                    return self._analyze_short_document(assignment_text, requirements_text)
                    
        except Exception as e:
            st.error(f"Error analyzing assignment: {e}")
            return None
    
    def _analyze_long_document(self, assignment_text, requirements_text=None):
        """Process long documents by chunking"""
        st.info("Document is large. Processing in chunks...")
        chunks = PDFProcessor.chunk_text(assignment_text)
        summaries = []
        
        progress_bar = st.progress(0)
        for i, chunk in enumerate(chunks):
            progress_bar.progress((i+1)/len(chunks))
            
            # Format the prompt with requirements if available
            prompt = LONG_CHUNK_ANALYSIS_PROMPT.format(
                requirements_context=f"The assignment is based on these requirements/questions:\n\n{requirements_text}\n\nWith the above requirements in mind, analyze this portion of the student's assignment:" if requirements_text else "Analyze this portion of an academic assignment:",
                chunk=chunk
            )
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            
            summaries.append(response.text)
        
        combined_summary = "\n\n".join(summaries)
        
        # Final analysis of the combined summaries
        return self._generate_final_assessment(combined_summary, requirements_text)
    
    def _analyze_short_document(self, assignment_text, requirements_text=None):
        """Process shorter documents directly"""
        # Format the prompt with requirements if available
        prompt = SHORT_DOCUMENT_ANALYSIS_PROMPT.format(
            requirements_context=f"The assignment is based on these requirements/questions:\n\n{requirements_text}\n\nWith the above requirements in mind, analyze this student assignment:" if requirements_text else "Analyze this student assignment:",
            assignment_text=assignment_text
        )
        
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        return self._parse_json_response(response.text)
    
    def _generate_final_assessment(self, combined_summary, requirements_text=None):
        """Generate final assessment from combined summaries"""
        # Format the prompt with requirements if available
        prompt = FINAL_ASSESSMENT_PROMPT.format(
            combined_summary=combined_summary,
            requirements_context=f"The assignment is based on these requirements/questions:\n\n{requirements_text}\n\nWith the above requirements in mind and based on these summaries, provide a comprehensive assessment:" if requirements_text else "Based on these summaries, provide a comprehensive assessment:"
        )
        
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        return self._parse_json_response(response.text)
    
    def _parse_json_response(self, response_text):
        """Extract and parse JSON from response"""
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_string = json_match.group(1)
        else:
            json_string = response_text
        
        try:
            result = json.loads(json_string)
            return result
        except json.JSONDecodeError:
            st.error("Error parsing AI response. Please try again.")
            st.code(response_text)
            return None
    
    def analyze_with_file_api(self, assignment_file_path, requirements_text=None):
        """Analyze PDF with Gemini using File API for non-extractable PDFs"""
        try:
            with st.spinner("Analyzing using advanced methods...", show_time=True):
                # Upload the PDF using the File API
                sample_file = self.client.files.upload(
                    file=assignment_file_path,
                )
                
                # Format prompt with requirements if available
                prompt = FILE_API_ANALYSIS_PROMPT.format(
                    requirements_context=f"The assignment is based on these requirements/questions:\n\n{requirements_text}\n\nWith these requirements in mind, analyze the attached student assignment PDF." if requirements_text else "Analyze the attached student assignment PDF."
                )
                
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[sample_file, prompt]
                )
                
                return self._parse_json_response(response.text)
                
        except Exception as e:
            st.error(f"Error analyzing PDF with File API: {e}")
            return None


class ReportGenerator:
    """Generates reports and visualizations from feedback data"""
    
    @staticmethod
    def create_markdown_report(feedback_data):
        """Create markdown report from feedback data"""
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
    
    @staticmethod
    def display_report(feedback_data):
        """Display report in Streamlit UI"""
        # Title and Grade Display
        st.header(feedback_data['title'])
        
        # Grade and Score
        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric(label="Grade", value=feedback_data['grade'])
        with col2:
            st.metric(label="Score", value=f"{feedback_data['score']}/100")
        
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
        
        # Category Scores with Charts
        st.subheader("Category Scores")
        
        # Create flexible column layout based on number of categories
        categories = list(feedback_data['category_scores'].keys())
        scores = list(feedback_data['category_scores'].values())
        
        # Display individual category scores with progress bars
        cols = st.columns(len(categories))
        for i, (category, score) in enumerate(feedback_data['category_scores'].items()):
            with cols[i]:
                st.metric(label=category, value=f"{score}/100")
                st.progress(score/100)
        
        # Visualization options
        viz_type = st.radio("Select Visualization Type:", 
                           ["Bar Chart", "Pie Chart"], 
                           horizontal=True)
        
        if viz_type == "Bar Chart":
            # Create bar chart with Plotly
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=categories,
                y=scores,
                marker=dict(
                    color='rgba(32, 156, 238, 0.8)',
                    line=dict(color='rgba(32, 156, 238, 1.0)', width=1)
                ),
                text=scores,
                textposition='auto'
            ))
            
            fig.update_layout(
                title="Category Performance",
                yaxis=dict(
                    title="Score",
                    range=[0, 100]
                ),
                xaxis_title="Categories",
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                plot_bgcolor='rgba(0,0,0,0.02)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:  # Pie Chart
            # Calculate percentages for better pie chart representation
            total = sum(scores)
            percentages = [score/total * 100 for score in scores]
            
            # Create pie chart with Plotly
            fig = go.Figure()
            
            fig.add_trace(go.Pie(
                labels=categories,
                values=scores,
                textinfo='label+percent',
                insidetextorientation='radial',
                marker=dict(
                    line=dict(color='#FFFFFF', width=1)
                ),
                pull=[0.05 if score == max(scores) else 0 for score in scores]  # Pull out the highest score slice
            ))
            
            fig.update_layout(
                title="Score Distribution by Category",
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=0, xanchor="center", x=0.5)
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add score comparison chart (horizontal bar)
            fig = go.Figure()
            
            # Sort categories and scores for better visualization
            sorted_pairs = sorted(zip(categories, scores), key=lambda x: x[1])
            sorted_categories, sorted_scores = zip(*sorted_pairs)
            
            fig.add_trace(go.Bar(
                y=sorted_categories,
                x=sorted_scores,
                orientation='h',
                marker=dict(
                    color=['rgba(255,80,80,0.7)' if score < 60 else 
                           'rgba(255,200,0,0.7)' if score < 75 else 
                           'rgba(46,204,113,0.7)' for score in sorted_scores],
                    line=dict(width=1)
                ),
                text=[f"{score}/100" for score in sorted_scores],
                textposition='auto'
            ))
            
            fig.update_layout(
                title="Performance Comparison",
                xaxis=dict(
                    title="Score",
                    range=[0, 100]
                ),
                height=300,
                margin=dict(l=20, r=20, t=40, b=20),
                plot_bgcolor='rgba(0,0,0,0.02)'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Detailed Feedback
        st.subheader("Detailed Feedback")
        st.write(feedback_data['detailed_feedback'])
        
        # Download options
        st.subheader("Download Report")
        
        md_content = ReportGenerator.create_markdown_report(feedback_data)
        st.download_button(
            label="Download as Markdown",
            data=md_content,
            file_name="assignment_feedback.md",
            mime="text/markdown"
        )


class PDFFeedbackApp:
    """Main application class"""
    
    def __init__(self):
        """Initialize application"""
        # Set page config
        st.set_page_config(
            page_title="AI PDF Feedback System",
            page_icon="📝",
            initial_sidebar_state="collapsed"
        )
        
        # Initialize session state
        if 'step' not in st.session_state:
            st.session_state.step = 1
        if 'assignment_file' not in st.session_state:
            st.session_state.assignment_file = None
        if 'requirements_file' not in st.session_state:
            st.session_state.requirements_file = None
        if 'assignment_text' not in st.session_state:
            st.session_state.assignment_text = None
        if 'requirements_text' not in st.session_state:
            st.session_state.requirements_text = None
        if 'feedback_data' not in st.session_state:
            st.session_state.feedback_data = None
        if 'temp_file_path' not in st.session_state:
            st.session_state.temp_file_path = None
        
        # Initialize components
        self.gemini = GeminiProcessor()
    
    def run(self):
        """Run the application"""
        st.title("🎓 AI PDF Feedback System")
        
        # Step 1: Upload assignment
        if st.session_state.step == 1:
            self._handle_step_1()
        
        # Step 2: Upload requirements (optional)
        elif st.session_state.step == 2:
            self._handle_step_2()
        
        # Step 3: Analysis
        elif st.session_state.step == 3:
            self._handle_step_3()
        
        # Step 4: Results
        elif st.session_state.step == 4:
            self._handle_step_4()
    
    def _handle_step_1(self):
        """Handle Step 1: Upload assignment"""
        st.header("Step 1: Upload Your Assignment")
        
        st.info("Upload your assignment PDF file to get feedback.")
        
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", key="assignment_uploader")
        
        if uploaded_file is not None:
            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
                st.session_state.temp_file_path = tmp_path
            
            st.session_state.assignment_file = uploaded_file
            
            # Extract text from PDF
            with st.spinner("Processing PDF...", show_time=True):
                st.session_state.assignment_text = PDFProcessor.extract_text_from_pdf(tmp_path)
                
                if st.session_state.assignment_text:
                    word_count = len(st.session_state.assignment_text.split())
                    st.success(f"✅ PDF uploaded and processed successfully! Word count: {word_count}")
                else:
                    st.warning("⚠️ Could not extract text from this PDF. We'll use advanced methods to analyze it.")
            
            # Proceed to next step
            if st.button("Continue to Step 2", type="primary"):
                st.session_state.step = 2
                st.rerun()
    
    def _handle_step_2(self):
        """Handle Step 2: Upload requirements (optional)"""
        st.header("Step 2: Upload Assignment Requirements (Optional)")
        
        st.info("Upload the assignment requirements or question paper to get more accurate feedback.")
        
        # Option to skip this step
        col1, col2 = st.columns([1, 1])
        
        with col1:
            requirements_option = st.radio(
                "Do you want to provide assignment requirements?",
                ["Yes, upload requirements", "Yes, enter requirements as text", "No, skip this step"]
            )
        
        if requirements_option == "Yes, upload requirements":
            uploaded_requirements = st.file_uploader("Choose a PDF file", type="pdf", key="requirements_uploader")
            
            if uploaded_requirements is not None:
                # Save the uploaded file to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                    tmp_file.write(uploaded_requirements.getvalue())
                    tmp_req_path = tmp_file.name
                
                # Extract text from PDF
                with st.spinner("Processing requirements PDF...", show_time=True):
                    st.session_state.requirements_text = PDFProcessor.extract_text_from_pdf(tmp_req_path)
                    
                    if st.session_state.requirements_text:
                        st.success("✅ Requirements PDF processed successfully!")
                    else:
                        st.error("❌ Could not extract text from the requirements PDF.")
                
                # Clean up temporary file
                os.unlink(tmp_req_path)
        
        elif requirements_option == "Yes, enter requirements as text":
            st.session_state.requirements_text = st.text_area(
                "Enter assignment requirements or question paper:",
                height=200
            )
        
        else:
            st.session_state.requirements_text = None
        
        # Navigation buttons
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("← Back to Step 1"):
                st.session_state.step = 1
                st.rerun()
        
        with col2:
            if st.button("Continue to Analysis →", type="primary"):
                st.session_state.step = 3
                st.rerun()
    
    def _handle_step_3(self):
        """Handle Step 3: Analysis"""
        st.header("Step 3: Analyzing Your Assignment")
        
        if st.session_state.feedback_data is None:
            # Show analysis information
            st.info("Our AI is analyzing your assignment. This may take a minute...")
            
            # Perform analysis based on text extraction success
            if st.session_state.assignment_text:
                # Process with extracted text
                st.session_state.feedback_data = self.gemini.analyze_with_extracted_text(
                    st.session_state.assignment_text,
                    st.session_state.requirements_text
                )
            else:
                # Process with file API
                st.session_state.feedback_data = self.gemini.analyze_with_file_api(
                    st.session_state.temp_file_path,
                    st.session_state.requirements_text
                )
            
            # Move to results
            if st.session_state.feedback_data:
                st.session_state.step = 4
                st.rerun()
            else:
                st.error("❌ Analysis failed. Please try again.")
                if st.button("← Back to Step 1"):
                    st.session_state.step = 1
                    st.rerun()
        else:
            # Should not reach here, but just in case
            st.success("Analysis complete!")
            if st.button("View Results →", type="primary"):
                st.session_state.step = 4
                st.rerun()
    
    def _handle_step_4(self):
        """Handle Step 4: Results"""
        st.header("Step 4: Feedback Results")
        
        if st.session_state.feedback_data:
            # Display report
            ReportGenerator.display_report(st.session_state.feedback_data)
            
            # Start new analysis button
            if st.button("Start New Analysis", type="primary"):
                # Clean up temporary file if it exists
                if st.session_state.temp_file_path and os.path.exists(st.session_state.temp_file_path):
                    os.unlink(st.session_state.temp_file_path)
                
                # Reset session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                
                st.session_state.step = 1
                st.rerun()
        else:
            st.error("❌ No feedback data available. Please start over.")
            if st.button("Start Over", type="primary"):
                st.session_state.step = 1
                st.rerun()


# Main entry point
if __name__ == "__main__":
    app = PDFFeedbackApp()
    app.run()