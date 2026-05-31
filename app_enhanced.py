"""
DASH - Enhanced AI Exam Evaluation System
With OCR, NLP, Grammar Check, Email & Analytics
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import csv
import uuid
import os
import sys
import warnings
warnings.filterwarnings('ignore')

# Add user site-packages to path
user_site = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', 
                         f'Python{sys.version_info.major}{sys.version_info.minor}', 'site-packages')
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

# Core imports
import PyPDF2
import pandas as pd
from datetime import datetime

# AI & ML imports (optional)
try:
    import google.generativeai as genai
    AI_ENABLED = True
    print("✓ Google Generative AI loaded")
except ImportError:
    AI_ENABLED = False
    print("⚠ Google AI not available")

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    NLP_ENABLED = True
    print("✓ NLP models loaded")
except ImportError:
    NLP_ENABLED = False
    print("⚠ NLP models not available")

try:
    import language_tool_python
    GRAMMAR_ENABLED = True
    print("✓ Grammar checker loaded")
except ImportError:
    GRAMMAR_ENABLED = False
    print("⚠ Grammar checker not available")

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
    EMAIL_ENABLED = True
    print("✓ Email service loaded")
except ImportError:
    EMAIL_ENABLED = False
    print("⚠ Email service not available")

# OCR imports (optional)
try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_ENABLED = True
    print("✓ OCR enabled")
except ImportError:
    OCR_ENABLED = False
    print("⚠ OCR not available")

app = Flask(__name__, template_folder='UI/templates', static_folder='UI/static')
app.secret_key = 'your_secret_key_here_change_in_production'

# Directory setup
QUESTIONS_DIR = r'Database\questions'
UPLOAD_FOLDER = r'Database\uploads'
RESULTS_FOLDER = r'Database\results'
os.makedirs(QUESTIONS_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# API Keys
from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_KEY_1", "")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")

# CSV paths
TEST_DETAILS_CSV = r"Database\test_details.csv"
STUDENT_DETAILS_CSV = r"Database\student_details.csv"
RESULTS_CSV = r"Database\results.csv"

# Initialize NLP model (if available)
if NLP_ENABLED:
    try:
        nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ NLP model initialized")
    except:
        NLP_ENABLED = False
        print("⚠ NLP model initialization failed")

# Initialize grammar checker (if available)
if GRAMMAR_ENABLED:
    try:
        grammar_tool = language_tool_python.LanguageTool('en-US')
        print("✓ Grammar checker initialized")
    except:
        GRAMMAR_ENABLED = False
        print("⚠ Grammar checker initialization failed")

# ==================== HELPER FUNCTIONS ====================

def read_pdf_with_ocr(file_path):
    """Extract text from PDF using OCR for handwritten/scanned documents"""
    if not OCR_ENABLED:
        return None
    
    try:
        print(f"  Using OCR for: {file_path}")
        images = convert_from_path(file_path)
        text = ""
        
        for i, image in enumerate(images):
            print(f"  Processing page {i+1}/{len(images)}...")
            page_text = pytesseract.image_to_string(image, lang='eng')
            text += page_text + "\n"
        
        return text.strip()
    except Exception as e:
        print(f"  OCR Error: {e}")
        return None

def read_pdf(file_path):
    """Extract text from PDF (tries normal extraction first, then OCR)"""
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            
            if len(reader.pages) == 0:
                return None
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            # If no text extracted, try OCR
            if not text.strip() and OCR_ENABLED:
                print("  No text found, trying OCR...")
                text = read_pdf_with_ocr(file_path)
            
            return text.strip() if text else None
            
    except Exception as e:
        print(f"  PDF Error: {e}")
        return None

def check_grammar(text):
    """Check grammar and return corrections"""
    if not GRAMMAR_ENABLED:
        return {"errors": 0, "suggestions": []}
    
    try:
        matches = grammar_tool.check(text)
        suggestions = []
        
        for match in matches[:5]:  # Top 5 errors
            suggestions.append({
                "message": match.message,
                "context": match.context,
                "replacements": match.replacements[:3]
            })
        
        return {
            "errors": len(matches),
            "suggestions": suggestions
        }
    except Exception as e:
        print(f"Grammar check error: {e}")
        return {"errors": 0, "suggestions": []}

def calculate_semantic_similarity(answer1, answer2):
    """Calculate semantic similarity using NLP"""
    if not NLP_ENABLED:
        return 0.0
    
    try:
        embeddings = nlp_model.encode([answer1, answer2])
        similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
        return float(similarity)
    except Exception as e:
        print(f"Similarity error: {e}")
        return 0.0

def evaluate_answer_advanced(question, student_answer, model_answer, max_marks):
    """Advanced evaluation with NLP, grammar, and AI"""
    result = {
        "marks": 0,
        "max_marks": max_marks,
        "feedback": "",
        "grammar_score": 0,
        "semantic_score": 0,
        "ai_feedback": ""
    }
    
    # 1. Grammar Check (20% weightage)
    grammar_result = check_grammar(student_answer)
    grammar_errors = grammar_result["errors"]
    grammar_score = max(0, 100 - (grammar_errors * 5))  # -5% per error
    result["grammar_score"] = grammar_score
    
    # 2. Semantic Similarity (40% weightage)
    semantic_score = calculate_semantic_similarity(student_answer, model_answer) * 100
    result["semantic_score"] = semantic_score
    
    # 3. AI Evaluation (40% weightage)
    ai_score = 0
    if AI_ENABLED:
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""Question: {question}
Model Answer: {model_answer}
Student Answer: {student_answer}

Evaluate on:
1. Accuracy (0-100)
2. Completeness (0-100)
3. Relevance (0-100)

Return only: SCORE: X (where X is 0-100)"""
            
            response = model.generate_content(prompt)
            # Extract score from response
            score_text = response.text
            if "SCORE:" in score_text:
                ai_score = float(score_text.split("SCORE:")[1].strip().split()[0])
            result["ai_feedback"] = response.text
        except:
            ai_score = semantic_score  # Fallback
    else:
        ai_score = semantic_score
    
    # Calculate final marks
    final_score = (grammar_score * 0.2 + semantic_score * 0.4 + ai_score * 0.4)
    result["marks"] = round((final_score / 100) * max_marks, 2)
    
    # Generate feedback
    feedback_parts = []
    if grammar_errors > 0:
        feedback_parts.append(f"Grammar: {grammar_errors} errors found")
    if semantic_score < 50:
        feedback_parts.append("Content needs improvement")
    elif semantic_score < 75:
        feedback_parts.append("Good attempt, can be better")
    else:
        feedback_parts.append("Excellent answer!")
    
    result["feedback"] = ". ".join(feedback_parts)
    
    return result

def send_result_email(student_email, student_name, test_name, marks, total_marks):
    """Send result email to student"""
    if not EMAIL_ENABLED:
        print("Email service not available")
        return False
    
    try:
        message = Mail(
            from_email='noreply@dash-exam.com',
            to_emails=student_email,
            subject=f'Your Result: {test_name}',
            html_content=f"""
            <h2>Exam Result</h2>
            <p>Dear {student_name},</p>
            <p>Your result for <strong>{test_name}</strong>:</p>
            <p><strong>Marks: {marks}/{total_marks}</strong></p>
            <p>Percentage: {(marks/total_marks)*100:.2f}%</p>
            <p>Thank you!</p>
            """
        )
        
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code == 202
    except Exception as e:
        print(f"Email error: {e}")
        return False

def is_code_valid(test_code):
    """Check if test code exists"""
    try:
        df = pd.read_csv(TEST_DETAILS_CSV)
        if 'unique code' in df.columns:
            return test_code in df['unique code'].values
        elif 'Unique Test Code' in df.columns:
            return test_code in df['Unique Test Code'].values
        return False
    except:
        return False

def get_test_details(test_code):
    """Get test details"""
    try:
        with open(TEST_DETAILS_CSV, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                code = row.get('unique code') or row.get('Unique Test Code')
                if code == test_code:
                    return row
    except Exception as e:
        print(f"Error: {e}")
    return None

def load_questions(test_code):
    """Load questions"""
    file_path = os.path.join(QUESTIONS_DIR, f"{test_code}_questions.csv")
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            return df[['Questions', 'Marks']].to_dict(orient='records')
        except:
            pass
    return None

# ==================== ROUTES ====================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/teacher')
def teacher_portal():
    return render_template('Teacher_potral.html')

@app.route('/teacher/create_exam')
def create_exam():
    return render_template('TP_create_exam.html')

@app.route('/teacher/submit_test', methods=['POST'])
def submit_test_details():
    name = request.form['name']
    time = request.form['time']
    date = request.form['date']
    duration = request.form['duration']
    subject = request.form['subject']
    faculty = request.form['faculty']
    total_marks = request.form['total_marks']
    questions = request.form.getlist('questions')
    marks = request.form.getlist('marks')

    unique_test_code = str(uuid.uuid4())[:8]

    with open(TEST_DETAILS_CSV, 'a', newline='') as file:
        writer = csv.writer(file)
        if os.stat(TEST_DETAILS_CSV).st_size == 0:
            writer.writerow(["name", "time", "date", "duration", "subject", "faculty ", "total  marks", "unique code"])
        writer.writerow([name, time, date, duration, subject, faculty, total_marks, unique_test_code])

    questions_file = os.path.join(QUESTIONS_DIR, f"{unique_test_code}_questions.csv")
    with open(questions_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Questions", "Marks"])
        for q, m in zip(questions, marks):
            writer.writerow([q, m])

    return render_template('success.html', test_code=unique_test_code)

@app.route('/teacher/paper_checking')
def start_paper_checking():
    return render_template('start_paper_checking.html')

@app.route('/teacher/upload_and_check', methods=['POST'])
def upload_and_check():
    try:
        if not AI_ENABLED:
            return jsonify({"error": "AI module not available. Please update API key in app_enhanced.py"}), 500
        
        if 'question_paper' not in request.files or 'answer_sheet' not in request.files:
            return jsonify({"error": "Both files required"}), 400
        
        question_paper = request.files['question_paper']
        answer_sheet = request.files['answer_sheet']
        
        if question_paper.filename == '' or answer_sheet.filename == '':
            return jsonify({"error": "Please select both PDF files"}), 400
        
        if not question_paper.filename.endswith('.pdf') or not answer_sheet.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files allowed"}), 400
        
        qp_path = os.path.join(UPLOAD_FOLDER, f"qp_{uuid.uuid4().hex[:8]}.pdf")
        as_path = os.path.join(UPLOAD_FOLDER, f"as_{uuid.uuid4().hex[:8]}.pdf")
        
        question_paper.save(qp_path)
        answer_sheet.save(as_path)
        
        print("Extracting text from PDFs...")
        qp_text = read_pdf(qp_path)
        
        if not qp_text:
            return jsonify({"error": "Could not extract text from Question Paper. Try text-based PDF or enable OCR."}), 500
        
        as_text = read_pdf(as_path)
        
        if not as_text:
            return jsonify({"error": "Could not extract text from Answer Sheet. Try text-based PDF or enable OCR."}), 500
        
        print(f"Extracted {len(qp_text)} chars from QP, {len(as_text)} chars from AS")
        
        # Evaluate using AI
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""Question Paper:
{qp_text}

Answer Sheet:
{as_text}

Evaluate comprehensively:
1. Accuracy & correctness
2. Grammar & language quality
3. Completeness
4. Provide marks for each question
5. Overall feedback

Format clearly with question-wise evaluation."""

            response = model.generate_content(prompt)
            
            result_file = os.path.join(RESULTS_FOLDER, f"result_{uuid.uuid4().hex[:8]}.txt")
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return jsonify({"success": True, "evaluation": response.text}), 200
            
        except Exception as api_error:
            error_msg = str(api_error)
            if "API key not valid" in error_msg:
                return jsonify({"error": "Invalid API Key. Get free key from: https://aistudio.google.com/app/apikey"}), 500
            return jsonify({"error": f"AI Error: {error_msg}"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/teacher/results')
def view_results():
    results = []
    try:
        if os.path.exists(RESULTS_CSV):
            df = pd.read_csv(RESULTS_CSV)
            results = df.to_dict(orient='records')
    except:
        pass
    return render_template('teacher_results.html', results=results)

# Student routes
@app.route('/student')
def student_home():
    return render_template('Student_test_check.html')

@app.route('/student/verify_code', methods=['POST'])
def verify_code():
    test_code = request.form['test_code']
    if is_code_valid(test_code):
        session['test_code'] = test_code
        return redirect(url_for('student_login'))
    return render_template('Student_test_check.html', error="Invalid test code")

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        email = request.form['email']
        test_code = session.get('test_code')
        
        session['student_name'] = name
        session['student_roll'] = roll_number
        session['student_email'] = email
        
        with open(STUDENT_DETAILS_CSV, 'a', newline='') as file:
            writer = csv.writer(file)
            if os.stat(STUDENT_DETAILS_CSV).st_size == 0:
                writer.writerow(['Name', 'Roll Number', 'Email', 'Test Code', 'Timestamp'])
            writer.writerow([name, roll_number, email, test_code, datetime.now()])
        
        return redirect(url_for('test_instruction'))
    
    return render_template('Student_login_details.html', test_code=session.get('test_code'))

@app.route('/student/instructions', methods=['GET', 'POST'])
def test_instruction():
    if request.method == 'POST':
        return redirect(url_for('student_test_portal'))
    return render_template('Student_test_instruction.html')

@app.route('/student/test')
def student_test_portal():
    test_code = session.get('test_code')
    test_details = get_test_details(test_code)
    questions = load_questions(test_code)
    
    if test_details and questions:
        return render_template('Student_test_potral.html', 
                             test_details=test_details, 
                             questions=questions)
    return "Test not found", 404

@app.route('/student/submit', methods=['POST'])
def submit_test():
    return render_template('Student_test_submit.html')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("DASH - Enhanced Exam Evaluation System")
    print("="*60)
    print(f"AI Enabled: {AI_ENABLED}")
    print(f"NLP Enabled: {NLP_ENABLED}")
    print(f"OCR Enabled: {OCR_ENABLED}")
    print(f"Grammar Check: {GRAMMAR_ENABLED}")
    print(f"Email Service: {EMAIL_ENABLED}")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)
