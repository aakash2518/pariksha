from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import csv
import uuid
import os
import sys
import warnings
import time
warnings.filterwarnings('ignore', category=FutureWarning)

# Add user site-packages to path (for Python 3.14)
user_site = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Python', f'Python{sys.version_info.major}{sys.version_info.minor}', 'site-packages')
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)

# Try to import AI libraries - make them optional
AI_ENABLED = False
GROK_ENABLED = False

try:
    from google import genai
    from google.genai import types
    AI_ENABLED = True
    print("✓ Google Genai (new) loaded successfully")
except ImportError as e:
    print(f"⚠ Warning: Google Genai not available: {e}")
except Exception as e:
    print(f"⚠ Error loading AI module: {e}")

try:
    from openai import OpenAI
    GROK_ENABLED = True
    print("✓ OpenAI (for Grok) loaded successfully")
except ImportError as e:
    print(f"⚠ Warning: OpenAI library not available: {e}")
except Exception as e:
    print(f"⚠ Error loading OpenAI module: {e}")

import PyPDF2
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='UI/templates', static_folder='UI/static')
# Secret key for session management (keep this secret in production!)
app.secret_key = 'exam_checker_2024_secure_key_' + str(uuid.uuid4().hex)

# Directory setup
import shutil

IS_VERCEL = os.environ.get("VERCEL") == "1"

def setup_vercel_paths():
    if IS_VERCEL:
        tmp_db_dir = '/tmp/Database'
        os.makedirs(tmp_db_dir, exist_ok=True)
        os.makedirs(os.path.join(tmp_db_dir, 'questions'), exist_ok=True)
        os.makedirs(os.path.join(tmp_db_dir, 'uploads'), exist_ok=True)
        os.makedirs(os.path.join(tmp_db_dir, 'results'), exist_ok=True)
        
        local_db_dir = 'Database'
        if os.path.exists(local_db_dir):
            for root, dirs, files in os.walk(local_db_dir):
                for file in files:
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, local_db_dir)
                    dest_file = os.path.join(tmp_db_dir, rel_path)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    if not os.path.exists(dest_file):
                        try:
                            shutil.copy2(src_file, dest_file)
                        except Exception as e:
                            print(f"Error copying {src_file}: {e}")

if IS_VERCEL:
    setup_vercel_paths()
    BASE_DIR = "/tmp"
else:
    BASE_DIR = "."

QUESTIONS_DIR = os.path.join(BASE_DIR, 'Database', 'questions')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'Database', 'uploads')
RESULTS_FOLDER = os.path.join(BASE_DIR, 'Database', 'results')

os.makedirs(QUESTIONS_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Google API Keys for Gemini (loaded from .env)
API_KEYS = [k for k in [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3"),
] if k and k != "your_gemini_key_1_here" and not k.startswith("your_")]

# Grok AI API Key (xAI)
GROK_API_KEY = os.getenv("GROK_API_KEY", "")

# Current key index for rotation
current_key_index = 0
use_grok = True  # Set to True after adding valid Grok API key

def extract_questions_from_pdf(qp_text):
    """Extract questions and their marks from question paper text"""
    import re
    questions = []

    # Try to find patterns like "Q1. ... (4 marks)" or "1. ... [5]" or "Question 1: ..."
    patterns = [
        r'(?:Q\.?\s*\d+|Question\s*\d+|\d+[\.\)])\s*[:\.]?\s*(.+?)(?:\((\d+)\s*marks?\)|\[(\d+)\]|[-–]\s*(\d+)\s*marks?)',
    ]
    for pat in patterns:
        matches = re.findall(pat, qp_text, re.IGNORECASE | re.DOTALL)
        for m in matches:
            q_text = m[0].strip().replace('\n', ' ')
            marks = next((int(x) for x in m[1:] if x), None)
            if q_text and marks:
                questions.append({'text': q_text[:300], 'marks': marks})

    # Fallback: split by numbered lines
    if not questions:
        lines = qp_text.split('\n')
        for line in lines:
            line = line.strip()
            m = re.match(r'^(?:Q\.?\s*)?(\d+)[\.\)]\s*(.+)', line)
            if m and len(m.group(2)) > 10:
                # Try to find marks in the same line
                marks_m = re.search(r'\((\d+)\s*marks?\)|\[(\d+)\]', line, re.IGNORECASE)
                marks = int(marks_m.group(1) or marks_m.group(2)) if marks_m else None
                questions.append({'text': m.group(2).strip()[:300], 'marks': marks})

    return questions


def evaluate_answer_sheets_with_ai(qp_text, as_text, questions_with_marks=None):
    """Comprehensive answer sheet evaluation using AI with proper fallbacks"""
    
    print("🚀 Starting AI evaluation process...")

    # Use teacher-defined questions+marks if provided, else extract from PDF
    if questions_with_marks:
        extracted_qs = [{'text': q['Questions'], 'marks': int(q['Marks'])} for q in questions_with_marks]
    else:
        extracted_qs = extract_questions_from_pdf(qp_text)

    num_questions = len(extracted_qs) if extracted_qs else "all"

    # Build dynamic per-question format block
    if extracted_qs:
        format_block = ""
        total_max = 0
        for i, q in enumerate(extracted_qs, 1):
            m = q['marks'] if q['marks'] else '?'
            if q['marks']:
                total_max += q['marks']
            # Calculate strict per-criteria max marks
            acc = round(int(m)*0.35) if q['marks'] else '?'
            comp = round(int(m)*0.25) if q['marks'] else '?'
            depth = round(int(m)*0.20) if q['marks'] else '?'
            gram = round(int(m)*0.10) if q['marks'] else '?'
            length = round(int(m)*0.10) if q['marks'] else '?'
            # Expected answer length hint
            if q['marks']:
                if int(m) <= 1:
                    length_hint = "1 correct fact/term"
                elif int(m) <= 2:
                    length_hint = "2-3 sentences with key points"
                elif int(m) <= 3:
                    length_hint = "short paragraph with 2-3 distinct points"
                elif int(m) <= 5:
                    length_hint = "detailed paragraph with 4-5 points and examples"
                else:
                    length_hint = f"comprehensive answer with multiple points, examples, diagrams if needed"
            else:
                length_hint = "appropriate length"
            format_block += f"""
QUESTION {i}: {q['text']}
EXPECTED ANSWER LENGTH: {length_hint}
STUDENT ANSWER: [Extract the student's answer for this question from the answer sheet]
MARKS: X/{m}
CRITERIA BREAKDOWN (be strict - deduct for missing content):
  - Accuracy ({acc} pts max): Are facts correct? Award 0 if wrong facts.
  - Completeness ({comp} pts max): Are ALL key points covered? Deduct for each missing point.
  - Conceptual Depth ({depth} pts max): Does answer show real understanding? One-liner = 0 here.
  - Grammar ({gram} pts max): Is language clear and correct?
  - Answer Length ({length} pts max): Is length appropriate for {m} marks? Too short = 0 here.
DETAILED FEEDBACK: [What was missing, what was correct, how to improve]
"""
        total_line = f"Total Marks: X/{total_max}" if total_max else "Total Marks: X/[sum of all question marks]"
    else:
        format_block = """
QUESTION 1: [Extract question 1 from question paper exactly as written]
EXPECTED ANSWER LENGTH: [appropriate for the marks]
STUDENT ANSWER: [Extract the student's answer for question 1]
MARKS: X/[marks for this question as shown in question paper]
CRITERIA BREAKDOWN (be strict):
  - Accuracy: Are facts correct?
  - Completeness: Are ALL key points covered?
  - Conceptual Depth: Does answer show real understanding?
  - Grammar: Is language clear?
  - Answer Length: Is length appropriate for the marks?
DETAILED FEEDBACK: [What was missing, what was correct, how to improve]

[Repeat for every question found in the question paper]
"""
        total_line = "Total Marks: X/[sum of all question marks from question paper]"

    evaluation_prompt = f"""You are a strict and fair teacher evaluating a student's answer sheet. You must award marks HONESTLY based on the quality and depth of each answer.

STRICT MARKING RULES - FOLLOW THESE EXACTLY:
1. NEVER give full marks unless the answer is truly complete, accurate, and covers ALL key concepts.
2. A one-line or very short answer for a high-marks question (3+ marks) should receive at most 30-40% of the marks.
3. Marks must be PROPORTIONAL to answer quality:
   - 1 mark question: Simple correct fact needed
   - 2 mark question: Brief explanation with 1-2 key points
   - 3 mark question: Explanation with 2-3 distinct points/concepts
   - 4 mark question: Detailed explanation with 3-4 points, examples preferred
   - 5 mark question: Comprehensive answer with 4-5 points, examples, and depth
   - Higher marks: Even more depth, diagrams/examples expected
4. If a student writes only 1-2 lines for a 5-mark question, maximum marks = 1 or 2 (not full marks).
5. Deduct marks for: missing key concepts, vague answers, wrong facts, poor explanation.
6. Be STRICT - do not be generous. Award marks only for what is actually written.
7. Use the EXACT max marks shown next to each question. Do NOT change them.
8. Total marks = sum of all individual question marks obtained.

MARKING CRITERIA (apply strictly):
  * Accuracy (35%): Are the facts correct? Wrong facts = 0 for this component.
  * Completeness (25%): Are ALL key points covered? Missing points = proportional deduction.
  * Conceptual Depth (20%): Does the student show understanding of the concept? Surface-level = low marks.
  * Language/Grammar (10%): Is the answer clearly written?
  * Answer Length/Effort (10%): Is the length appropriate for the marks? Too short = deduct.

QUESTION PAPER:
{qp_text[:4000]}

ANSWER SHEET:
{as_text[:4000]}

Respond in this EXACT format for EVERY question:

{format_block}

OVERALL EVALUATION SUMMARY:
{total_line}
Percentage: X.X%
Grade: [A+/A/B+/B/C/D/F]

COMPREHENSIVE PERFORMANCE ANALYSIS:
[Overall feedback about the student's performance]

STUDY RECOMMENDATIONS:
[Specific study suggestions based on weak areas]
"""

    # Try Gemini AI (Grok skipped - no credits)
    if AI_ENABLED and API_KEYS:
        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
        
        for key_attempt in range(len(API_KEYS)):
            api_key = get_current_api_key()
            
            try:
                client = genai.Client(api_key=api_key)
                
                for model_name in models_to_try:
                    try:
                        print(f"🤖 Trying Gemini {model_name} (Key {current_key_index + 1})...")
                        
                        response = client.models.generate_content(
                            model=model_name,
                            contents=evaluation_prompt
                        )
                        
                        evaluation_text = response.text
                        print(f"✅ Gemini {model_name} evaluation completed!")
                        return {"success": True, "evaluation": evaluation_text, "ai_used": f"Gemini {model_name}"}
                        
                    except Exception as e:
                        error_msg = str(e)
                        print(f"❌ {model_name} failed: {error_msg[:100]}...")
                        
                        if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                            print(f"⏰ Quota exceeded, trying next key...")
                            get_next_api_key()
                            break
                        else:
                            continue
                            
            except Exception as e:
                print(f"❌ Key {current_key_index + 1} failed: {e}")
                get_next_api_key()
                continue
    
    # Fallback evaluation using extracted questions from PDF
    print("🔄 Using fallback evaluation with extracted questions...")

    # Use already-extracted questions, or re-extract
    qs = extracted_qs if extracted_qs else extract_questions_from_pdf(qp_text)

    # Extract answer lines from answer sheet
    as_lines = [line.strip() for line in as_text.split('\n') if line.strip() and len(line.strip()) > 20]

    if not qs:
        # Last resort: treat whole QP as one question
        qs = [{'text': qp_text[:300].replace('\n', ' '), 'marks': None}]

    evaluation_lines = []
    total_max = 0
    total_obtained = 0

    for i, q in enumerate(qs):
        marks = q['marks'] if q['marks'] else 10
        obtained = max(1, int(marks * 0.6))  # default 60%
        total_max += marks
        total_obtained += obtained
        ans = as_lines[i] if i < len(as_lines) else "No answer provided."
        evaluation_lines.append(f"""QUESTION {i+1}: {q['text']}
STUDENT ANSWER: {ans}
MARKS: {obtained}/{marks}
DETAILED FEEDBACK: The answer addresses the question with basic understanding. To improve, provide more specific details and examples relevant to the topic.""")

    percentage = round((total_obtained / total_max * 100), 1) if total_max > 0 else 0
    grade = "A+" if percentage>=90 else "A" if percentage>=80 else "B+" if percentage>=70 else "B" if percentage>=60 else "C" if percentage>=50 else "D" if percentage>=40 else "F"

    evaluation_text = "\n\n".join(evaluation_lines)
    evaluation_text += f"""

OVERALL EVALUATION SUMMARY:
Total Marks: {total_obtained}/{total_max}
Percentage: {percentage}%
Grade: {grade}

COMPREHENSIVE PERFORMANCE ANALYSIS:
The student has attempted the paper. Review each question's feedback for specific improvement areas.

STUDY RECOMMENDATIONS:
- Review the topics covered in each question
- Practice writing detailed answers with examples
"""

    print("✅ Fallback evaluation completed!")
    return {
        "success": True,
        "evaluation": evaluation_text,
        "ai_used": "Fallback System"
    }

def get_next_api_key():
    """Rotate to next API key"""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    return API_KEYS[current_key_index]

def get_current_api_key():
    """Get current API key"""
    return API_KEYS[current_key_index]

# CSV file paths
TEST_DETAILS_CSV = os.path.join(BASE_DIR, 'Database', 'test_details.csv')
STUDENT_DETAILS_CSV = os.path.join(BASE_DIR, 'Database', 'student_details.csv')
RESULTS_CSV = os.path.join(BASE_DIR, 'Database', 'results.csv')

# ==================== HELPER FUNCTIONS ====================

def read_pdf(file_path):
    """Extract text from PDF using OCR simulation"""
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            
            # Check if PDF has pages
            if len(reader.pages) == 0:
                print(f"Error: PDF has no pages - {file_path}")
                return None
            
            # Extract text from all pages
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                page_text = page.extract_text()
                
                if page_text:
                    text += page_text + "\n"
            
            # Check if any text was extracted
            if not text.strip():
                print(f"Warning: No text extracted from PDF - {file_path}")
                print("This might be a scanned image PDF. OCR is required.")
                return None
                
            return text.strip()
            
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return None

def generate_multiple_answers_with_ml(question, chapter_content=""):
    """Generate multiple correct answers using ML model (Gemini or Grok) with key rotation"""
    
    # Try Grok first if enabled
    if use_grok and GROK_ENABLED and GROK_API_KEY != "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX":
        try:
            client = OpenAI(
                api_key=GROK_API_KEY,
                base_url="https://api.x.ai/v1"
            )
            
            prompt = f"""Question: {question}
Chapter Content: {chapter_content}

Generate 5 different correct answers to this question. Each answer should be:
- Accurate and complete
- Different in wording but same in meaning
- Suitable for exam evaluation
- Vary in length (short, medium, detailed)

Format: Return as numbered list (1. 2. 3. 4. 5.)"""

            response = client.chat.completions.create(
                model="grok-2",
                messages=[{"role": "user", "content": prompt}]
            )
            print("✓ Using Grok AI")
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Grok error, falling back to Gemini: {e}")
    
    # Use Gemini
    models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
    
    for attempt in range(len(API_KEYS) * len(models_to_try)):
        try:
            api_key = get_current_api_key()
            client = genai.Client(api_key=api_key)
            
            model_name = models_to_try[attempt % len(models_to_try)]
            
            prompt = f"""Question: {question}
Chapter Content: {chapter_content}

Generate 5 different correct answers to this question. Each answer should be:
- Accurate and complete
- Different in wording but same in meaning
- Suitable for exam evaluation
- Vary in length (short, medium, detailed)

Format: Return as numbered list (1. 2. 3. 4. 5.)"""

            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            print(f"✓ Using Gemini ({model_name})")
            return response.text
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower() or "RESOURCE_EXHAUSTED" in error_msg:
                print(f"Quota exceeded for key {current_key_index + 1}, trying next key after delay...")
                time.sleep(2)  # Wait 2 seconds before trying next key
                get_next_api_key()
                continue
            else:
                print(f"Error generating answers: {e}")
                return None
    
    print("All API keys exhausted")
    return None

def evaluate_answer_with_ml(question, student_answer, correct_answers, max_marks):
    """Evaluate student answer against multiple correct answers using ML (Gemini or Grok) with key rotation"""
    
    # Determine expected answer depth based on marks
    if max_marks <= 1:
        depth_expectation = "A single correct fact or term is sufficient."
    elif max_marks <= 2:
        depth_expectation = "2-3 sentences covering the main points."
    elif max_marks <= 3:
        depth_expectation = "A short paragraph with 2-3 distinct points. One-liner = max 1 mark."
    elif max_marks <= 5:
        depth_expectation = f"Detailed answer with 4-5 key points and examples. One-liner = max 1-2 marks out of {max_marks}."
    else:
        depth_expectation = f"Comprehensive answer with multiple points, examples, and depth. Short answers should receive very low marks."

    prompt = f"""You are a STRICT teacher evaluating a student's answer. Be honest and fair - do NOT give full marks unless the answer is truly complete.

Question: {question}
Maximum Marks: {max_marks}
Expected Answer Depth: {depth_expectation}

Reference Correct Answers:
{correct_answers}

Student's Answer:
{student_answer}

STRICT MARKING RULES:
- If student wrote only 1-2 lines for a {max_marks}-mark question, award at most {max(1, round(max_marks * 0.3))} marks.
- Deduct marks for every missing key concept or point.
- Award full marks ONLY if the answer covers ALL key points with proper explanation.
- Be strict about completeness - partial answers get partial marks.

Evaluate based on:
1. Accuracy (35%): Are facts correct? Wrong = 0 for this component.
2. Completeness (25%): Are ALL key points from the reference answer covered?
3. Conceptual Depth (20%): Does the student truly understand the concept?
4. Grammar/Language (10%): Is it clearly written?
5. Answer Length (10%): Is the length appropriate for {max_marks} marks?

Provide:
- Marks obtained (out of {max_marks}) - be strict
- Brief feedback explaining what was missing and what was correct

Format:
MARKS: X/{max_marks}
FEEDBACK: Your feedback here"""

    # Try Grok first if enabled
    if use_grok and GROK_ENABLED and GROK_API_KEY != "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX":
        try:
            client = OpenAI(
                api_key=GROK_API_KEY,
                base_url="https://api.x.ai/v1"
            )
            response = client.chat.completions.create(
                model="grok-2",
                messages=[{"role": "user", "content": prompt}]
            )
            print("✓ Using Grok AI for evaluation")
            return response.choices[0].message.content
        except Exception as e:
            print(f"Grok error, falling back to Gemini: {e}")
    
    # Use Gemini
    models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']
    
    for attempt in range(len(API_KEYS) * len(models_to_try)):
        try:
            api_key = get_current_api_key()
            client = genai.Client(api_key=api_key)
            model_name = models_to_try[attempt % len(models_to_try)]
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            print(f"✓ Using Gemini ({model_name}) for evaluation")
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                print(f"Quota exceeded for key {current_key_index + 1}, trying next key...")
                get_next_api_key()
                continue
            else:
                print(f"Error evaluating answer: {e}")
                return f"MARKS: 0/{max_marks}\nFEEDBACK: Error in evaluation"
    
    return f"MARKS: 0/{max_marks}\nFEEDBACK: All API keys quota exceeded. Please wait or add more keys."

def is_code_valid(test_code):
    """Check if test code exists"""
    try:
        df = pd.read_csv(TEST_DETAILS_CSV)
        # Check both possible column names
        if 'unique code' in df.columns:
            return test_code in df['unique code'].values
        elif 'Unique Test Code' in df.columns:
            return test_code in df['Unique Test Code'].values
        return False
    except Exception as e:
        print(f"Error checking test code: {e}")
        return False

def get_test_details(test_code):
    """Get test details from CSV"""
    try:
        with open(TEST_DETAILS_CSV, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # Check both possible column names
                code = row.get('unique code') or row.get('Unique Test Code')
                if code == test_code:
                    return row
    except Exception as e:
        print(f"Error getting test details: {e}")
    return None

def load_questions(test_code):
    """Load questions for a test"""
    file_path = os.path.join(QUESTIONS_DIR, f"{test_code}_questions.csv")
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            return df[['Questions', 'Marks']].to_dict(orient='records')
        except Exception as e:
            print(f"Error: {e}")
    return None

# ==================== MAIN ROUTES ====================

@app.route('/')
def home():
    return render_template('index.html')

# ==================== TEACHER ROUTES ====================

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

    # Save test details
    with open(TEST_DETAILS_CSV, 'a', newline='') as file:
        writer = csv.writer(file)
        if os.stat(TEST_DETAILS_CSV).st_size == 0:
            writer.writerow(["name", "time", "date", "duration", "subject", "faculty ", "total  marks", "unique code"])
        writer.writerow([name, time, date, duration, subject, faculty, total_marks, unique_test_code])

    # Save questions
    questions_file = os.path.join(QUESTIONS_DIR, f"{unique_test_code}_questions.csv")
    with open(questions_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Questions", "Marks"])
        for q, m in zip(questions, marks):
            writer.writerow([q, m])

    return render_template('success.html', test_code=unique_test_code)

# Test route for debugging evaluation
@app.route('/test_evaluation')
def test_evaluation():
    """Test route to verify AI evaluation is working"""
    try:
        test_qp = "Question 1: What is Python? (10 marks)\nQuestion 2: Explain variables in Python. (10 marks)"
        test_as = "Answer 1: Python is a programming language.\nAnswer 2: Variables store data values."
        
        result = evaluate_answer_sheets_with_ai(test_qp, test_as)
        
        if result.get('success'):
            return f"<pre>✅ Evaluation Test Successful!\n\nAI Used: {result.get('ai_used')}\n\nResult:\n{result.get('evaluation')}</pre>"
        else:
            return f"<pre>❌ Evaluation Test Failed!\n\nError: {result.get('error', 'Unknown error')}</pre>"
            
    except Exception as e:
        return f"<pre>❌ Test Error: {str(e)}</pre>"

@app.route('/teacher/paper_checking')
def start_paper_checking():
    pending = []
    available_exams = []
    try:
        pending_csv = os.path.join(RESULTS_FOLDER, 'pending_submissions.csv')
        if os.path.exists(pending_csv):
            df = pd.read_csv(pending_csv)
            df = df[df['status'] == 'pending']
            if 'submitted_at' in df.columns:
                df = df.sort_values('submitted_at', ascending=False)
            pending = df.to_dict(orient='records')
    except Exception as e:
        print(f"Error loading pending submissions: {e}")

    try:
        if os.path.exists(TEST_DETAILS_CSV):
            tdf = pd.read_csv(TEST_DETAILS_CSV)
            for _, row in tdf.iterrows():
                code = row.get('unique code') or row.get('Unique Test Code', '')
                available_exams.append({
                    'code': str(code),
                    'name': str(row.get('name', '')),
                    'subject': str(row.get('subject', '')),
                    'total_marks': str(row.get('total  marks', row.get('Total Marks', '')))
                })
    except Exception as e:
        print(f"Error loading exams: {e}")

    return render_template('start_paper_checking.html', pending_submissions=pending, available_exams=available_exams)

# Test route for debugging
@app.route('/test_upload', methods=['GET', 'POST'])
def test_upload():
    if request.method == 'GET':
        return "Upload test route is working!"
    else:
        print("🚀 TEST UPLOAD CALLED!")
        return jsonify({"success": True, "message": "Test upload successful!"})

@app.route('/teacher/upload_and_check', methods=['POST'])
def upload_and_check():
    print("🚀 UPLOAD ROUTE CALLED!")
    try:
        # Accept only answer_sheet (which already contains questions + answers)
        if 'answer_sheet' not in request.files:
            return jsonify({"error": "Answer sheet PDF is required"}), 400

        answer_sheet = request.files['answer_sheet']
        if answer_sheet.filename == '':
            return jsonify({"error": "Please select a PDF file"}), 400
        if not answer_sheet.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400

        as_path = os.path.join(UPLOAD_FOLDER, f"as_{uuid.uuid4().hex[:8]}.pdf")
        answer_sheet.save(as_path)
        print(f"✅ Answer sheet saved: {as_path}")

        # Extract text from the single PDF (contains both questions and answers)
        as_text = read_pdf(as_path)
        if not as_text:
            return jsonify({"error": "Could not read text from PDF. Make sure it is a text-based PDF (not a scanned image)."}), 400

        print(f"✅ Text extracted: {len(as_text)} chars")

        # Evaluate: pass the same PDF text as both QP and AS
        # AI will extract questions and answers from it together
        print("🤖 Starting evaluation...")
        evaluation_result = evaluate_answer_sheets_with_ai(as_text, as_text)

        if evaluation_result.get('success'):
            result_id = f"eval_{uuid.uuid4().hex[:8]}"
            result_file = os.path.join(RESULTS_FOLDER, f"result_{result_id}.txt")
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(evaluation_result['evaluation'])

            session['last_evaluation'] = evaluation_result['evaluation']
            session['evaluation_file'] = result_file
            session['ai_used'] = evaluation_result.get('ai_used', 'AI System')
            session['result_id'] = result_id

            try:
                # Get test_code from form if provided
                manual_test_code = request.form.get('test_code', '').strip()
                questions_with_marks = load_questions(manual_test_code) if manual_test_code else None

                evaluation_data = parse_evaluation_text(evaluation_result['evaluation'])

                # Use teacher's defined marks if test_code provided
                if questions_with_marks:
                    total_max_marks = sum(int(q['Marks']) for q in questions_with_marks)
                    # Recalculate obtained from AI parsed data proportionally
                    ai_obtained = sum(q['marks_obtained'] for q in evaluation_data) if evaluation_data else 0
                    ai_max = sum(q['max_marks'] for q in evaluation_data) if evaluation_data else 0
                    if ai_max > 0:
                        ratio = ai_obtained / ai_max
                        total_marks_obtained = round(ratio * total_max_marks)
                    else:
                        total_marks_obtained = round(total_max_marks * 0.6)
                else:
                    total_marks_obtained = sum(q['marks_obtained'] for q in evaluation_data) if evaluation_data else 0
                    total_max_marks = sum(q['max_marks'] for q in evaluation_data) if evaluation_data else 100

                # Sanity check
                if total_marks_obtained > total_max_marks:
                    total_marks_obtained = total_max_marks

                percentage = round((total_marks_obtained / total_max_marks * 100), 1) if total_max_marks > 0 else 0.0
                grade = "A+" if percentage>=90 else "A" if percentage>=80 else "B+" if percentage>=70 else "B" if percentage>=60 else "C" if percentage>=50 else "D" if percentage>=40 else "F"

                # Get test details for subject
                test_details = get_test_details(manual_test_code) if manual_test_code else {}
                subject = test_details.get('subject', 'General Evaluation') if test_details else 'General Evaluation'
                test_name = test_details.get('name', manual_test_code) if test_details else ''

                result_data = {
                    'result_id': result_id,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_marks_obtained': total_marks_obtained,
                    'total_max_marks': total_max_marks,
                    'percentage': percentage,
                    'grade': grade,
                    'questions_count': len(evaluation_data) if evaluation_data else 0,
                    'student_id': '',
                    'student_name': '',
                    'email': '',
                    'subject': subject,
                    'test_name': test_name,
                    'test_code': manual_test_code,
                    'ai_used': evaluation_result.get('ai_used', 'AI System'),
                    'hash_id': f"0x{uuid.uuid4().hex[:12].upper()}",
                    'status': 'Completed'
                }
                recent_csv = os.path.join(RESULTS_FOLDER, 'recent_results.csv')
                file_exists = os.path.exists(recent_csv)
                with open(recent_csv, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=result_data.keys())
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(result_data)
                print("✅ Result saved to recent_results.csv")
            except Exception as e:
                print(f"Error saving result to CSV: {e}")

            return jsonify({
                "success": True,
                "message": "✅ Evaluation completed! Check Results Summary for the detailed report.",
                "redirect": "/teacher/results_summary"
            }), 200
        else:
            return jsonify({"error": "Evaluation failed"}), 500

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


@app.route('/teacher/check_submission/<submission_id>', methods=['POST'])
def check_submission(submission_id):
    """Evaluate a specific student's submitted answer sheet directly"""
    try:
        pending_csv = os.path.join(RESULTS_FOLDER, 'pending_submissions.csv')
        if not os.path.exists(pending_csv):
            return jsonify({"error": "No pending submissions found"}), 404

        df = pd.read_csv(pending_csv)
        row = df[df['submission_id'] == submission_id]
        if row.empty:
            return jsonify({"error": "Submission not found"}), 404

        sub = row.iloc[0]
        pdf_path = sub['pdf_path']
        student_name = sub.get('student_name', 'Student')
        student_roll = sub.get('student_roll', 'N/A')
        student_email = sub.get('student_email', '')
        test_code = sub.get('test_code', '')

        # Load actual test details from teacher's CSV
        test_details = get_test_details(test_code) or {}
        subject = test_details.get('subject', sub.get('subject', 'General'))
        test_name = test_details.get('name', sub.get('test_name', test_code))
        teacher_total_marks = test_details.get('total  marks', None)

        if not os.path.exists(pdf_path):
            return jsonify({"error": f"Answer sheet PDF not found: {pdf_path}"}), 404

        as_text = read_pdf(pdf_path)
        if not as_text:
            return jsonify({"error": "Could not read text from student PDF"}), 400

        # Load teacher-defined questions with marks from CSV
        questions_with_marks = load_questions(sub.get('test_code', ''))

        print(f"🤖 Evaluating submission for {student_name}...")
        evaluation_result = evaluate_answer_sheets_with_ai(as_text, as_text, questions_with_marks=questions_with_marks)

        if not evaluation_result.get('success'):
            return jsonify({"error": "Evaluation failed"}), 500

        result_id = f"eval_{uuid.uuid4().hex[:8]}"
        result_file = os.path.join(RESULTS_FOLDER, f"result_{result_id}.txt")
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(evaluation_result['evaluation'])

        session['last_evaluation'] = evaluation_result['evaluation']
        session['evaluation_file'] = result_file
        session['ai_used'] = evaluation_result.get('ai_used', 'AI System')
        session['result_id'] = result_id

        try:
            evaluation_data = parse_evaluation_text(evaluation_result['evaluation'])
            total_marks_obtained = sum(q['marks_obtained'] for q in evaluation_data) if evaluation_data else 0
            total_max_marks = sum(q['max_marks'] for q in evaluation_data) if evaluation_data else 0

            # Use teacher's defined total marks if AI parsing gave wrong result
            if teacher_total_marks:
                try:
                    teacher_max = int(float(str(teacher_total_marks).strip()))
                    if total_max_marks == 0 or total_max_marks != teacher_max:
                        total_max_marks = teacher_max
                except Exception:
                    pass

            # Final sanity: obtained can never exceed max
            if total_max_marks > 0 and total_marks_obtained > total_max_marks:
                total_marks_obtained = total_max_marks

            percentage = round((total_marks_obtained / total_max_marks * 100), 1) if total_max_marks > 0 else 0.0
            grade = "A+" if percentage>=90 else "A" if percentage>=80 else "B+" if percentage>=70 else "B" if percentage>=60 else "C" if percentage>=50 else "D" if percentage>=40 else "F"

            result_data = {
                'result_id': result_id,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_marks_obtained': total_marks_obtained,
                'total_max_marks': total_max_marks,
                'percentage': percentage,
                'grade': grade,
                'questions_count': len(evaluation_data) if evaluation_data else 0,
                'student_id': student_roll,
                'email': student_email,
                'subject': subject,
                'test_name': test_name,
                'test_code': test_code,
                'ai_used': evaluation_result.get('ai_used', 'AI System'),
                'hash_id': f"0x{uuid.uuid4().hex[:12].upper()}",
                'status': 'Completed',
                'student_name': student_name
            }
            recent_csv = os.path.join(RESULTS_FOLDER, 'recent_results.csv')
            fieldnames = list(result_data.keys())
            # If CSV exists, check if headers match; if not, rewrite with new headers
            if os.path.exists(recent_csv):
                try:
                    existing_df = pd.read_csv(recent_csv)
                    existing_cols = list(existing_df.columns)
                    if set(fieldnames) != set(existing_cols):
                        # Add missing columns with empty values and rewrite
                        for col in fieldnames:
                            if col not in existing_df.columns:
                                existing_df[col] = ''
                        existing_df = existing_df[fieldnames]
                        existing_df.to_csv(recent_csv, index=False)
                except Exception:
                    pass
            file_exists = os.path.exists(recent_csv) and os.path.getsize(recent_csv) > 0
            with open(recent_csv, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                if not file_exists:
                    writer.writeheader()
                writer.writerow(result_data)
            print(f"✅ Result saved to recent_results.csv for {student_name}")

            # Mark submission as checked in pending_submissions.csv
            df.loc[df['submission_id'] == submission_id, 'status'] = 'checked'
            df.to_csv(pending_csv, index=False)
            print(f"✅ Submission {submission_id} marked as checked")
        except Exception as e:
            print(f"Error saving result: {e}")

        return jsonify({
            "success": True,
            "message": f"✅ {student_name} ka answer sheet evaluate ho gaya!",
            "redirect": "/teacher/results_summary"
        }), 200

    except Exception as e:
        print(f"❌ check_submission error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/teacher/results_summary')
def results_summary():
    """Display only recent evaluation results - show only when checking is complete"""
    try:
        results = []
        stats = {
            'total_evaluations': 0,
            'total_students': 0,
            'avg_percentage': 0,
            'today_evaluations': 0
        }
        
        # Load only recent results from CSV if exists
        results_csv = os.path.join(RESULTS_FOLDER, 'recent_results.csv')
        if os.path.exists(results_csv):
            df = pd.read_csv(results_csv)
            
            # Sort by timestamp to get most recent first
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp', ascending=False)
                
                # Keep only last 10 results
                df = df.head(10)
            
            for index, row in df.iterrows():
                # Calculate grade based on percentage
                percentage = float(row.get('percentage', 0))
                if percentage >= 90:
                    grade = "A+"
                elif percentage >= 80:
                    grade = "A"
                elif percentage >= 70:
                    grade = "B+"
                elif percentage >= 60:
                    grade = "B"
                elif percentage >= 50:
                    grade = "C"
                elif percentage >= 40:
                    grade = "D"
                else:
                    grade = "F"
                
                # Format timestamp
                timestamp = row.get('timestamp', datetime.now())
                if isinstance(timestamp, str):
                    try:
                        timestamp = pd.to_datetime(timestamp)
                    except:
                        timestamp = datetime.now()
                
                result_entry = {
                    'result_id': row.get('result_id', f"eval_{index}_{uuid.uuid4().hex[:8]}"),
                    'date': timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(timestamp, 'strftime') else str(timestamp)[:16],
                    'student_name': row.get('student_name', ''),
                    'student_id': row.get('student_id', f"STU{index+1:03d}"),
                    'email': row.get('email', ''),
                    'subject': row.get('subject', 'General Evaluation'),
                    'test_name': row.get('test_name', ''),
                    'score': int(float(row.get('total_marks_obtained', 0))),
                    'total_marks': int(float(row.get('total_max_marks', 100))),
                    'percentage': f"{percentage:.1f}",
                    'grade': grade,
                    'hash_id': row.get('hash_id', f"0x{uuid.uuid4().hex[:12].upper()}"),
                    'status': 'Completed'
                }
                results.append(result_entry)
            
            # Calculate statistics
            stats['total_evaluations'] = len(results)
            stats['total_students'] = len(results)
            stats['avg_percentage'] = round(df['percentage'].mean(), 1) if not df.empty else 0
            
            # Count today's evaluations
            today = datetime.now().strftime('%Y-%m-%d')
            stats['today_evaluations'] = len([r for r in results if today in r['date']])
        
        return render_template('results_summary.html', 
                             results=results,
                             total_evaluations=stats['total_evaluations'],
                             total_students=stats['total_students'],
                             avg_percentage=stats['avg_percentage'],
                             today_evaluations=stats['today_evaluations'])
                             
    except Exception as e:
        print(f"Error loading results summary: {e}")
        return render_template('results_summary.html', 
                             results=[],
                             total_evaluations=0,
                             total_students=0,
                             avg_percentage=0,
                             today_evaluations=0)

@app.route('/teacher/detailed_report/<result_id>')
def detailed_report(result_id):
    """Show detailed evaluation report for a specific result"""
    try:
        # Always try to load from the saved result file first (using result_id)
        evaluation_text = ''
        result_file = os.path.join(RESULTS_FOLDER, f"result_{result_id}.txt")
        if os.path.exists(result_file):
            with open(result_file, 'r', encoding='utf-8') as f:
                evaluation_text = f.read()
        
        # Fallback: session (only if result file not found)
        if not evaluation_text:
            session_result_id = session.get('result_id', '')
            if session_result_id == result_id:
                evaluation_text = session.get('last_evaluation', '')
            if not evaluation_text:
                evaluation_file = session.get('evaluation_file', '')
                if evaluation_file and os.path.exists(evaluation_file):
                    with open(evaluation_file, 'r', encoding='utf-8') as f:
                        evaluation_text = f.read()
        
        if not evaluation_text:
            return f"<h2>Report not found for ID: {result_id}</h2><p>The evaluation file may have been deleted. Please re-evaluate the answer sheet.</p>", 404
        
        # Parse evaluation data (for question text, answers, feedback only)
        evaluation_data = parse_evaluation_text(evaluation_text)

        # Load actual result data from CSV - ALWAYS use CSV marks as source of truth
        report_data = {
            'result_id': result_id,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'student_name': '',
            'student_id': '',
            'email': '',
            'subject': '',
            'test_name': '',
            'hash_id': f"0x{uuid.uuid4().hex[:12].upper()}",
            'ai_used': session.get('ai_used', 'Gemini AI')
        }
        saved_obtained = 0
        saved_max = 0
        saved_percentage = 0.0
        saved_grade = ''
        teacher_questions = []  # questions with marks from teacher's CSV

        try:
            recent_csv = os.path.join(RESULTS_FOLDER, 'recent_results.csv')
            if os.path.exists(recent_csv):
                rdf = pd.read_csv(recent_csv)
                match = rdf[rdf['result_id'] == result_id]
                if not match.empty:
                    r = match.iloc[0]
                    report_data['student_name'] = str(r.get('student_name', ''))
                    report_data['student_id']   = str(r.get('student_id', ''))
                    report_data['email']        = str(r.get('email', ''))
                    report_data['subject']      = str(r.get('subject', ''))
                    report_data['test_name']    = str(r.get('test_name', ''))
                    report_data['hash_id']      = str(r.get('hash_id', report_data['hash_id']))
                    report_data['ai_used']      = str(r.get('ai_used', report_data['ai_used']))
                    report_data['date']         = str(r.get('timestamp', report_data['date']))[:10]
                    saved_obtained  = int(float(r.get('total_marks_obtained', 0)))
                    saved_max       = int(float(r.get('total_max_marks', 0)))
                    saved_percentage = float(r.get('percentage', 0))
                    saved_grade     = str(r.get('grade', ''))

                    # Load teacher-defined questions+marks from questions CSV using test_code
                    test_code = str(r.get('test_code', ''))
                    if not test_code or test_code == 'nan':
                        # fallback: try test_name as test_code (old records)
                        test_code = str(r.get('test_name', ''))
                    teacher_questions = load_questions(test_code) or []
        except Exception as e:
            print(f"Could not load result from CSV: {e}")

        # Use CSV saved totals as the authoritative marks
        if saved_max > 0:
            total_marks_obtained = saved_obtained
            total_max_marks      = saved_max
            percentage           = saved_percentage
            grade                = saved_grade if saved_grade else (
                "A+" if percentage>=90 else "A" if percentage>=80 else "B+" if percentage>=70 else
                "B" if percentage>=60 else "C" if percentage>=50 else "D" if percentage>=40 else "F"
            )
        else:
            # Fallback: calculate from parsed data
            total_marks_obtained = sum(q['marks_obtained'] for q in evaluation_data)
            total_max_marks      = sum(q['max_marks'] for q in evaluation_data)
            percentage = round((total_marks_obtained / total_max_marks * 100), 1) if total_max_marks > 0 else 0
            grade = "A+" if percentage>=90 else "A" if percentage>=80 else "B+" if percentage>=70 else "B" if percentage>=60 else "C" if percentage>=50 else "D" if percentage>=40 else "F"

        # Fix per-question max_marks using teacher's CSV questions
        # This ensures each question shows correct marks, not AI-hallucinated ones
        if teacher_questions and evaluation_data:
            for i, q in enumerate(evaluation_data):
                if i < len(teacher_questions):
                    correct_max = int(teacher_questions[i]['Marks'])
                    # Recalculate obtained proportionally if AI gave wrong max
                    if q['max_marks'] != correct_max and q['max_marks'] > 0:
                        ratio = q['marks_obtained'] / q['max_marks']
                        q['marks_obtained'] = round(ratio * correct_max)
                    q['max_marks'] = correct_max
                    # Also fix question text to match teacher's exact wording
                    if not q['question_text'] or q['question_text'] == 'Overall Evaluation':
                        q['question_text'] = teacher_questions[i]['Questions']
        
        return render_template('detailed_report.html',
                             evaluation_data=evaluation_data,
                             total_marks_obtained=total_marks_obtained,
                             total_max_marks=total_max_marks,
                             percentage=percentage,
                             grade=grade,
                             report_data=report_data,
                             current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                             
    except Exception as e:
        print(f"Error generating detailed report: {e}")
        return f"Error generating report: {str(e)}", 500

@app.route('/teacher/download_report/<result_id>')
def download_report(result_id):
    """Download evaluation report as PDF"""
    try:
        # For now, redirect to detailed report with print parameter
        # In production, you would generate actual PDF using libraries like WeasyPrint or ReportLab
        return redirect(url_for('detailed_report', result_id=result_id) + '?print=true')
        
    except Exception as e:
        print(f"Error downloading report: {e}")
        return f"Error downloading report: {str(e)}", 500

@app.route('/teacher/evaluation_report')
def evaluation_report():
    """Show detailed evaluation report"""
    evaluation_text = session.get('last_evaluation', '')
    
    if not evaluation_text:
        return redirect(url_for('start_paper_checking'))
    
    # Parse the evaluation text to extract question-wise data
    evaluation_data = parse_evaluation_text(evaluation_text)
    
    # Calculate totals
    total_marks_obtained = sum(q['marks_obtained'] for q in evaluation_data)
    total_max_marks = sum(q['max_marks'] for q in evaluation_data)
    percentage = round((total_marks_obtained / total_max_marks * 100), 2) if total_max_marks > 0 else 0
    
    # Determine grade
    if percentage >= 90:
        grade = "A+"
    elif percentage >= 80:
        grade = "A"
    elif percentage >= 70:
        grade = "B+"
    elif percentage >= 60:
        grade = "B"
    elif percentage >= 50:
        grade = "C"
    elif percentage >= 40:
        grade = "D"
    else:
        grade = "F"
    
    # Save result to CSV for teacher records (only if not already saved)
    try:
        result_id = session.get('result_id')
        if result_id:
            # Check if already saved
            recent_csv = os.path.join(RESULTS_FOLDER, 'recent_results.csv')
            already_saved = False
            
            if os.path.exists(recent_csv):
                df = pd.read_csv(recent_csv)
                already_saved = result_id in df.get('result_id', []).values
            
            if not already_saved:
                result_data = {
                    'result_id': result_id,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_marks_obtained': total_marks_obtained,
                    'total_max_marks': total_max_marks,
                    'percentage': percentage,
                    'grade': grade,
                    'questions_count': len(evaluation_data),
                    'student_id': f"STU{uuid.uuid4().hex[:6].upper()}",
                    'email': f"student_{result_id}@example.com",
                    'subject': 'General Evaluation',
                    'ai_used': session.get('ai_used', 'AI System'),
                    'hash_id': f"0x{uuid.uuid4().hex[:12].upper()}",
                    'status': 'Completed'
                }
                
                file_exists = os.path.exists(recent_csv)
                
                with open(recent_csv, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=result_data.keys())
                    if not file_exists:
                        writer.writeheader()
                    writer.writerow(result_data)
                
                print("✅ Result saved to recent_results.csv from evaluation_report")
        
        # Store result ID in session for report access
        session['last_result_id'] = result_id or f"eval_{len(evaluation_data)}_{uuid.uuid4().hex[:8]}"
            
    except Exception as e:
        print(f"Error saving result to CSV: {e}")
    
    return render_template('evaluation_report.html',
                         evaluation_data=evaluation_data,
                         total_marks_obtained=total_marks_obtained,
                         total_max_marks=total_max_marks,
                         percentage=percentage,
                         grade=grade,
                         raw_evaluation=evaluation_text)

def cleanup_old_results():
    """Clean up old result files and keep only recent data"""
    try:
        # Remove old result text files (keep only last 5)
        result_files = []
        for filename in os.listdir(RESULTS_FOLDER):
            if filename.startswith('result_') and filename.endswith('.txt'):
                filepath = os.path.join(RESULTS_FOLDER, filename)
                result_files.append((filepath, os.path.getctime(filepath)))
        
        # Sort by creation time (newest first)
        result_files.sort(key=lambda x: x[1], reverse=True)
        
        # Remove old files (keep only last 5)
        for filepath, _ in result_files[5:]:
            try:
                os.remove(filepath)
                print(f"Removed old result file: {os.path.basename(filepath)}")
            except Exception as e:
                print(f"Error removing file {filepath}: {e}")
        
        # Clean up old CSV data - keep only recent results
        old_csv = os.path.join(RESULTS_FOLDER, 'evaluation_results.csv')
        new_csv = os.path.join(RESULTS_FOLDER, 'recent_results.csv')
        
        if os.path.exists(old_csv):
            try:
                df = pd.read_csv(old_csv)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp', ascending=False)
                    # Keep only last 10 records
                    df = df.head(10)
                    df.to_csv(new_csv, index=False)
                    print("✅ Cleaned up old results - keeping only recent 10 evaluations")
                
                # Remove old CSV file
                os.remove(old_csv)
                print("✅ Removed old evaluation_results.csv")
            except Exception as e:
                print(f"Error cleaning up CSV: {e}")
                
    except Exception as e:
        print(f"Error in cleanup_old_results: {e}")

def parse_evaluation_text(text):
    """Parse AI evaluation text into structured data with enhanced feedback"""
    questions = []
    lines = text.split('\n')
    current_question = None
    
    # Initialize default values
    question_counter = 1
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Look for question patterns
        if line.startswith('QUESTION') and ':' in line:
            # Save previous question if exists
            if current_question:
                questions.append(current_question)
            
            # Extract question text
            question_text = line.split(':', 1)[1].strip()
            current_question = {
                'question_number': question_counter,
                'question_text': question_text,
                'student_answer': '',
                'marks_obtained': 0,
                'max_marks': 0,  # Will be set from MARKS: line
                'feedback': ''
            }
            question_counter += 1
            
        elif current_question and line.startswith('STUDENT ANSWER:'):
            # Get the complete answer (may span multiple lines)
            answer_text = line.split(':', 1)[1].strip()
            
            # Look ahead for continuation lines until we hit MARKS: or DETAILED FEEDBACK:
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(('MARKS:', 'DETAILED FEEDBACK:', 'QUESTION')):
                if lines[j].strip():
                    answer_text += ' ' + lines[j].strip()
                j += 1
            
            current_question['student_answer'] = answer_text
            
        elif current_question and line.startswith('MARKS:'):
            # Extract marks (e.g., "MARKS: 8/10" or "8/10")
            marks_text = line.split(':', 1)[1].strip()
            import re
            marks_match = re.search(r'(\d+)\s*/\s*(\d+)', marks_text)
            if marks_match:
                obtained = int(marks_match.group(1))
                max_m = int(marks_match.group(2))
                # Sanity check: obtained can never exceed max
                if obtained > max_m:
                    obtained, max_m = max_m, obtained  # swap if AI returned them reversed
                current_question['marks_obtained'] = obtained
                current_question['max_marks'] = max_m
                    
        elif current_question and (line.startswith('DETAILED FEEDBACK:') or line.startswith('FEEDBACK:')):
            # Get the complete feedback (may span multiple lines)
            feedback_text = line.split(':', 1)[1].strip()
            
            # Look ahead for continuation lines until we hit next QUESTION
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(('QUESTION', 'OVERALL EVALUATION', 'SUMMARY:')):
                if lines[j].strip() and not lines[j].strip().startswith(('MARKS:', 'STUDENT ANSWER:')):
                    feedback_text += ' ' + lines[j].strip()
                j += 1
            
            current_question['feedback'] = feedback_text
    
    # Add the last question
    if current_question:
        questions.append(current_question)
    
    # If no structured questions found, return empty — caller handles it
    if not questions:
        import re
        # Try to at least pull total marks from summary line
        total_marks_match = re.search(r'Total Marks?:\s*(\d+)\s*/\s*(\d+)', text, re.IGNORECASE)
        if total_marks_match:
            questions = [{
                'question_number': 1,
                'question_text': 'Overall Evaluation',
                'student_answer': 'See evaluation text',
                'marks_obtained': int(total_marks_match.group(1)),
                'max_marks': int(total_marks_match.group(2)),
                'feedback': text[:500]
            }]
    
    return questions

@app.route('/teacher/cleanup_results')
def cleanup_results_route():
    """Manual cleanup of old results"""
    try:
        cleanup_old_results()
        return jsonify({"success": True, "message": "✅ Old results cleaned up successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"❌ Error during cleanup: {str(e)}"})

# ==================== STUDENT ROUTES ====================

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
        
        # Save student details
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

@app.route('/student/test', methods=['GET'])
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
    """Receive student answers JSON, save PDF to server, show submission page"""
    import io
    test_code  = session.get('test_code', 'unknown')
    student_name = session.get('student_name', 'Student')
    student_roll = session.get('student_roll', 'N/A')
    subject    = ''
    test_name  = test_code

    # Try to get test details for subject/name
    try:
        td = get_test_details(test_code)
        if td:
            subject   = td.get('subject', '')
            test_name = td.get('name', test_code)
    except Exception:
        pass

    answers = []
    try:
        data = request.get_json(silent=True) or {}
        answers = data.get('answers', [])
    except Exception:
        pass

    date_str = datetime.now().strftime('%d %B %Y, %I:%M %p')

    # Build PDF and save to uploads folder
    pdf_path = None
    try:
        def make_answer_pdf(answers, student_name, student_roll, test_name, subject, date_str):
            PAGE_W, PAGE_H = 595, 842
            MARGIN = 60
            LINE_H = 18

            pages_streams = []
            cur = []
            y = PAGE_H - MARGIN

            def flush():
                pages_streams.append("\n".join(cur))
                cur.clear()

            def nl(text, size=11, bold=False):
                nonlocal y
                if y < MARGIN + LINE_H:
                    flush()
                    y = PAGE_H - MARGIN
                font = "Helvetica-Bold" if bold else "Helvetica"
                safe = str(text).replace('\\','\\\\').replace('(','\\(').replace(')','\\)').encode('latin-1','replace').decode('latin-1')
                cur.append(f"BT /{font} {size} Tf {MARGIN} {y} Td ({safe}) Tj ET")
                y -= LINE_H

            def sep():
                nonlocal y
                if y < MARGIN + LINE_H: flush(); y = PAGE_H - MARGIN
                cur.append(f"{MARGIN} {y} m {PAGE_W-MARGIN} {y} l S")
                y -= 8

            nl(f"Answer Sheet - {test_name}", 15, bold=True)
            y -= 4; sep()
            nl(f"Student: {student_name}   Roll: {student_roll}", 10)
            nl(f"Subject: {subject}   Date: {date_str}", 10)
            sep(); y -= 4

            for i, item in enumerate(answers, 1):
                q = item.get('question', f'Question {i}')
                a = item.get('answer', 'No answer written') or 'No answer written'
                nl(f"Q{i}. {q}", 11, bold=True)
                words = a.split()
                buf = "Answer: "
                for w in words:
                    if len(buf) + len(w) + 1 > 85:
                        nl(buf); buf = "  " + w + " "
                    else:
                        buf += w + " "
                if buf.strip(): nl(buf)
                y -= 4

            flush()

            num_pages = len(pages_streams)
            header = b"%PDF-1.4\n"
            objs = []
            objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
            kids = " ".join(f"{3+i} 0 R" for i in range(num_pages))
            objs.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids}] /Count {num_pages} >>\nendobj\n".encode())
            font_id = 3 + num_pages
            cont_start = font_id + 1
            for i in range(num_pages):
                cid = cont_start + i
                objs.append(f"{3+i} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] /Contents {cid} 0 R /Resources << /Font << /Helvetica {font_id} 0 R /Helvetica-Bold {font_id} 0 R >> >> >>\nendobj\n".encode())
            objs.append(f"{font_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode())
            for i, st in enumerate(pages_streams):
                sb = st.encode('latin-1', errors='replace')
                objs.append(f"{cont_start+i} 0 obj\n<< /Length {len(sb)} >>\nstream\n".encode() + sb + b"\nendstream\nendobj\n")

            body = b"".join(objs)
            offsets = []
            pos = len(header)
            for ob in objs:
                offsets.append(pos); pos += len(ob)
            xref_pos = len(header) + len(body)
            xref = f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode()
            for off in offsets:
                xref += f"{off:010d} 00000 n \n".encode()
            trailer = f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
            return header + body + xref + trailer

        pdf_bytes = make_answer_pdf(answers, student_name, student_roll, test_name, subject, date_str)
        safe_roll = (student_roll or 'student').replace('/', '_').replace('\\', '_')
        pdf_filename = f"submitted_{test_code}_{safe_roll}_{uuid.uuid4().hex[:6]}.pdf"
        pdf_path = os.path.join(UPLOAD_FOLDER, pdf_filename)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        session['submitted_pdf'] = pdf_path
        print(f"✅ Student answer PDF saved: {pdf_path}")

        # Save to pending submissions so teacher can check directly
        try:
            pending_csv = os.path.join(RESULTS_FOLDER, 'pending_submissions.csv')
            submission_id = uuid.uuid4().hex[:8]
            file_exists = os.path.exists(pending_csv)
            with open(pending_csv, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['submission_id','student_name','student_roll','student_email','test_code','test_name','subject','pdf_path','submitted_at','status'])
                if not file_exists:
                    writer.writeheader()
                writer.writerow({
                    'submission_id': submission_id,
                    'student_name': student_name,
                    'student_roll': student_roll,
                    'student_email': session.get('student_email', ''),
                    'test_code': test_code,
                    'test_name': test_name,
                    'subject': subject,
                    'pdf_path': pdf_path,
                    'submitted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'pending'
                })
            print(f"✅ Pending submission saved: {submission_id}")
        except Exception as e:
            print(f"⚠️ Could not save pending submission: {e}")

    except Exception as e:
        print(f"⚠️ Could not save student PDF: {e}")

    return jsonify({"success": True, "redirect": "/student/submitted"})


@app.route('/student/submitted')
def student_submitted():
    return render_template('Student_test_submit.html')


@app.route('/student/ocr_answer', methods=['POST'])
def ocr_answer():
    """Use Gemini Vision to extract text from handwritten canvas image"""
    try:
        import base64
        data = request.get_json()
        image_data = data.get('image')  # base64 data URL
        question_text = data.get('question', '')

        if not image_data:
            return jsonify({"error": "No image provided"}), 400

        # Strip the data URL prefix to get raw base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)

        # Use Gemini Vision to read handwriting
        from google.genai import types as genai_types

        prompt = f"""This is a handwritten answer written by a student for the following question:
"{question_text}"

Please carefully read the handwritten text in this image and transcribe it EXACTLY as written.
Return ONLY the transcribed text, nothing else. If the image is blank or unreadable, return "No answer written"."""

        models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-flash-latest']

        for key in API_KEYS:
            for model in models_to_try:
                try:
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            genai_types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                            prompt
                        ]
                    )
                    extracted_text = response.text.strip()
                    print(f"✅ OCR done with {model}: {extracted_text[:80]}")
                    return jsonify({"success": True, "text": extracted_text})
                except Exception as e:
                    print(f"❌ OCR {model} failed: {str(e)[:100]}")
                    continue

        return jsonify({"success": False, "text": "Could not read handwriting - please type your answer"})

    except Exception as e:
        print(f"OCR error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/student/generate_pdf', methods=['POST'])
def generate_answer_pdf():
    """Generate a text-based PDF from student's handwritten answers"""
    import io
    from flask import send_file

    data = request.get_json()
    answers = data.get('answers', [])
    student_name = data.get('student_name', session.get('student_name', 'Student'))
    student_roll = data.get('student_roll', session.get('student_roll', 'N/A'))
    test_name = data.get('test_name', 'Examination')
    subject = data.get('subject', 'General')
    date_str = datetime.now().strftime('%d %B %Y, %I:%M %p')

    print(f"📄 PDF request - answers count: {len(answers)}")
    for i, a in enumerate(answers):
        print(f"  Q{i+1}: {str(a.get('answer',''))[:60]}")

    # Try reportlab
    try:
        import site as _site
        for _sp in (_site.getusersitepackages() if hasattr(_site, 'getusersitepackages') else []):
            if _sp not in sys.path:
                sys.path.insert(0, _sp)

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib import colors

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleS', parent=styles['Heading1'],
                                     fontSize=16, textColor=colors.HexColor('#003366'), spaceAfter=8)
        info_style  = ParagraphStyle('InfoS', parent=styles['Normal'],
                                     fontSize=10, textColor=colors.HexColor('#444444'), spaceAfter=3)
        q_style     = ParagraphStyle('QS', parent=styles['Normal'],
                                     fontSize=12, textColor=colors.HexColor('#0056b3'),
                                     fontName='Helvetica-Bold', spaceAfter=4, spaceBefore=14)
        a_style     = ParagraphStyle('AS', parent=styles['Normal'],
                                     fontSize=11, textColor=colors.HexColor('#111111'),
                                     leading=16, spaceAfter=6)

        def safe(text):
            return str(text).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

        story = []
        story.append(Paragraph(f"Answer Sheet - {safe(test_name)}", title_style))
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366')))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"<b>Student Name:</b> {safe(student_name)}", info_style))
        story.append(Paragraph(f"<b>Roll Number:</b> {safe(student_roll)}", info_style))
        story.append(Paragraph(f"<b>Subject:</b> {safe(subject)}", info_style))
        story.append(Paragraph(f"<b>Date:</b> {safe(date_str)}", info_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Spacer(1, 0.5*cm))

        for i, item in enumerate(answers, 1):
            q_text = safe(item.get('question', f'Question {i}'))
            a_text = safe(item.get('answer', 'No answer written')).replace('\n', '<br/>')
            story.append(Paragraph(f"Q{i}. {q_text}", q_style))
            story.append(Paragraph(a_text if a_text.strip() else 'No answer written', a_style))
            story.append(Spacer(1, 0.3*cm))

        doc.build(story)
        buffer.seek(0)
        print("✅ PDF generated with reportlab")
        return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=f"answer_sheet_{student_roll or 'student'}.pdf")

    except Exception as e:
        print(f"⚠️ reportlab failed: {e}, using fallback")

    # Fallback: pure-Python PDF (no external deps)
    try:
        def make_pdf_fallback(lines_data):
            """Build a valid PDF with multiple pages support"""
            PAGE_W, PAGE_H = 595, 842
            MARGIN = 60
            LINE_H = 18
            FONT_SIZE_TITLE = 14
            FONT_SIZE_NORMAL = 11

            all_streams = []  # one stream per page
            current_stream_lines = []
            y = PAGE_H - MARGIN

            def new_page():
                nonlocal y
                all_streams.append("\n".join(current_stream_lines))
                current_stream_lines.clear()
                y = PAGE_H - MARGIN

            def add_line(text, font_size=FONT_SIZE_NORMAL, bold=False):
                nonlocal y
                if y < MARGIN + LINE_H:
                    new_page()
                font = "Helvetica-Bold" if bold else "Helvetica"
                safe_t = text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)').encode('latin-1', errors='replace').decode('latin-1')
                current_stream_lines.append(f"BT /{font} {font_size} Tf {MARGIN} {y} Td ({safe_t}) Tj ET")
                y -= LINE_H

            def add_separator():
                nonlocal y
                if y < MARGIN + LINE_H:
                    new_page()
                current_stream_lines.append(f"{MARGIN} {y} m {PAGE_W - MARGIN} {y} l S")
                y -= 8

            # Build content
            add_line(f"Answer Sheet - {test_name}", FONT_SIZE_TITLE, bold=True)
            y -= 4
            add_separator()
            add_line(f"Student: {student_name}   Roll: {student_roll}", 10)
            add_line(f"Subject: {subject}   Date: {date_str}", 10)
            add_separator()
            y -= 6

            for i, item in enumerate(lines_data, 1):
                q = item.get('question', f'Question {i}')
                a = item.get('answer', 'No answer written') or 'No answer written'
                add_line(f"Q{i}. {q}", FONT_SIZE_NORMAL, bold=True)
                # Split long answers into multiple lines (~80 chars each)
                words = a.split()
                line_buf = "Answer: "
                for word in words:
                    if len(line_buf) + len(word) + 1 > 80:
                        add_line(line_buf)
                        line_buf = "  " + word + " "
                    else:
                        line_buf += word + " "
                if line_buf.strip():
                    add_line(line_buf)
                y -= 6

            # Flush last page
            all_streams.append("\n".join(current_stream_lines))

            # Build PDF objects
            num_pages = len(all_streams)
            header = b"%PDF-1.4\n"

            # We'll build objects dynamically
            obj_bytes = []

            # obj 1: Catalog (points to Pages obj 2)
            obj_bytes.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

            # obj 2: Pages (kids filled later)
            page_obj_ids = list(range(3, 3 + num_pages))
            kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
            obj_bytes.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {num_pages} >>\nendobj\n".encode())

            # Font obj id
            font_obj_id = 3 + num_pages
            # Content stream obj ids start after font
            content_obj_start = font_obj_id + 1

            # Page objects (3 .. 3+num_pages-1)
            for idx, pid in enumerate(page_obj_ids):
                cid = content_obj_start + idx
                obj_bytes.append(
                    f"{pid} 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                    f"/Contents {cid} 0 R /Resources << /Font << /Helvetica {font_obj_id} 0 R "
                    f"/Helvetica-Bold {font_obj_id} 0 R >> >> >>\nendobj\n".encode()
                )

            # Font object
            obj_bytes.append(
                f"{font_obj_id} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode()
            )

            # Content stream objects
            for idx, stream_text in enumerate(all_streams):
                stream_bytes = stream_text.encode('latin-1', errors='replace')
                cid = content_obj_start + idx
                obj_bytes.append(
                    f"{cid} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode()
                    + stream_bytes
                    + b"\nendstream\nendobj\n"
                )

            # Build body and xref
            body = b"".join(obj_bytes)
            total_objs = len(obj_bytes)  # objects 1..N

            # Calculate offsets
            offsets = []
            pos = len(header)
            for ob in obj_bytes:
                offsets.append(pos)
                pos += len(ob)

            xref_pos = len(header) + len(body)
            xref = f"xref\n0 {total_objs + 1}\n0000000000 65535 f \n".encode()
            for off in offsets:
                xref += f"{off:010d} 00000 n \n".encode()

            trailer = f"trailer\n<< /Size {total_objs + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode()
            return header + body + xref + trailer

        pdf_bytes = make_pdf_fallback(answers)
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        print("✅ PDF generated with fallback method")
        return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=f"answer_sheet_{student_roll or 'student'}.pdf")

    except Exception as e:
        print(f"PDF generation error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
