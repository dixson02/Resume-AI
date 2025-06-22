from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import Optional
import os
from dotenv import load_dotenv
import subprocess
import logging
from pypdf import PdfReader
from docx import Document
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
import time
from promt import prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))  

app = FastAPI()

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
SUPPORTED_TYPES = ['.pdf', '.docx']

# --- Text Extraction ---
def extract_text(file: UploadFile) -> str:
    """Extract text from PDF or DOCX with validation"""
    try:
        # Validate file type
        if not any(file.filename.endswith(ext) for ext in SUPPORTED_TYPES):
            raise HTTPException(status_code=400, detail=f"Unsupported file type. Supported: {SUPPORTED_TYPES}")
        
        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset pointer
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Max size: {MAX_FILE_SIZE//1024//1024}MB")
        
        # Extract text
        if file.filename.endswith('.pdf'):
            pdf = PdfReader(file.file)
            return " ".join(page.extract_text() for page in pdf.pages if page.extract_text())
        else:  # DOCX
            doc = Document(file.file)
            return " ".join(para.text for para in doc.paragraphs if para.text)
            
    except Exception as e:
        logger.error(f"Text extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to extract text from file")

# --- Gemini Analysis ---
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def analyze_with_gemini(resume_text: str) -> str:
    """Analyze resume with Gemini with retry logic"""
    try:
        start_time = time.time()
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            prompt.format(resume_text=resume_text),
            generation_config={
                "max_output_tokens": 2000,
                "temperature": 0.3
            }
        )
        logger.info(f"Gemini analysis completed in {time.time()-start_time:.2f}s")
        return response.text
    except Exception as e:
        logger.error(f"Gemini analysis failed: {str(e)}")
        raise

# --- API Endpoint ---
@app.post('/analyze')  # Fixed typo from 'analyze' to match function name
async def analyze_resume(file: UploadFile = File(...)):
    """Endpoint to analyze resumes with proper error handling"""
    try:
        text = extract_text(file)
        
        try:
            feedback = analyze_with_gemini(text)
            return {
                "filename": file.filename,
                "analysis": feedback,
                "llm_source": "Gemini-1.5-Flash",
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Analysis failed after retries: {str(e)}")
            return {
                "filename": file.filename,
                "analysis": "Failed to analyze resume. Please try again later.",
                "llm_source": "None",
                "status": "error"
            }
            
    except HTTPException as http_err:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.critical(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")