# AI PDF Feedback System

A Streamlit application that uses Google Gemini AI to analyze academic assignments and provide comprehensive feedback.

## Overview

The AI PDF Feedback System is designed to help educators and students by automatically analyzing academic assignments submitted in PDF format. The application extracts text from PDFs, analyzes the content using Google's Gemini AI, and generates detailed feedback including grades, scores, strengths, areas for improvement, and category-specific assessments.

## Features

- **PDF Document Processing**: Upload and extract text from PDF assignments
- **AI-Powered Analysis**: Utilize Google Gemini AI for comprehensive assessment
- **Smart Chunking**: Handle large documents by splitting them into manageable chunks
- **Interactive Visualizations**: View performance across different assessment categories
- **Downloadable Reports**: Save feedback as Markdown files
- **Clean Interface**: Intuitive Streamlit UI with sidebar navigation

## Installation

### Prerequisites

- Python 3.8 or higher
- Google Gemini API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/ai-pdf-feedback-system.git
   cd ai-pdf-feedback-system
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install streamlit python-dotenv pymupdf4llm pandas matplotlib plotly google-generativeai
   ```

4. Create a `.env` file in the project root and add your Google Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

1. Run the Streamlit application:
   ```bash
   streamlit run main.py
   ```

2. Access the application in your web browser at `http://localhost:8501`

3. Upload a PDF document using the sidebar

4. Click "Analyze Assignment" to process the document

5. Review the comprehensive feedback including:
   - Overall grade and score
   - Category-specific scores with visualizations
   - Summary of the work
   - Strengths and areas for improvement
   - Detailed feedback

6. Download the feedback report in Markdown format

## How It Works

1. **Document Upload**: The user uploads a PDF document through the Streamlit interface
2. **Text Extraction**: The system extracts text from the PDF using pymupdf4llm
3. **Content Analysis**:
   - For shorter documents, the entire text is analyzed at once
   - For longer documents, the text is split into chunks and analyzed separately
4. **AI Assessment**: Google Gemini AI generates comprehensive feedback
5. **Visualization**: The feedback is displayed with interactive charts
6. **Report Generation**: Users can download the feedback as a Markdown file

## Technologies Used

- **Streamlit**: Web application framework
- **Google Gemini AI**: Advanced language model for content analysis
- **pymupdf4llm**: PDF text extraction
- **Plotly**: Interactive data visualization
- **Python-dotenv**: Environment variable management

## Configuration

You can configure the application by modifying the following parameters:

- Maximum chunk size for document processing (default: 8000 characters)
- Gemini AI model (default: "gemini-2.0-flash")
- Category scoring metrics (Content, Structure, Analysis, Language, References)

## Limitations

- The system relies on text extraction, so PDFs with complex layouts or primarily image-based content may not be analyzed accurately
- Performance depends on the quality and availability of the Google Gemini API
- The system is designed for academic assignments and may not provide accurate feedback for other types of documents

## Future Improvements

- Add support for more document formats (DOCX, TXT, etc.)
- Implement custom rubric creation for assessment
- Add comparative analysis between multiple assignments
- Integrate with learning management systems
- Add user authentication and assignment history
