from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import csv
import uuid
import os
import sys

# Force add the user site-packages path
import site
user_site = site.getusersitepackages()
if user_site not in sys.path:
    sys.path.insert(0, user_site)

print(f"Python: {sys.executable}")
print(f"User site: {user_site}")

# Now try importing
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

AI_ENABLED = False
try:
    import google.generativeai as genai
    AI_ENABLED = True
    print("✓ Google Generative AI loaded successfully!")
except Exception as e:
    print(f"✗ Google AI Error: {e}")
    print(f"  Try: {sys.executable} -m pip install --user google-generativeai")

import PyPDF2
import pandas as pd
from datetime import datetime

app = Flask(__name__, template_folder='UI/templates', static_folder='UI/static')
app.secret_key = 'your_secret_key_change_in_production'

# Directories
QUESTIONS_DIR = r'Database\questions'
UPLOAD_FOLDER = r'Database\uploads'
RESULTS_FOLDER = r'Database\results'
os.makedirs(QUESTIONS_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# API Key - Your Real Key
from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_KEY_1", "")

# CSV paths
TEST_DETAILS_CSV = r"Database\test_details.csv"
STUDENT_DETAILS_CSV = r"Database\student_details.csv"
RESULTS_CSV = r"Database\results.csv"

def read_pdf(file_path):
    """Extract text from PDF"""
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
            return text.strip() if text else None
    except Exception as e:
        print(f"PDF Error: {e}")
        return None

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
            for row in csv.DictReader(file):
                code = row.get('unique code') or row.get('Unique Test Code')
                if code == test_code:
                    return row
    except:
        pass
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
    """Landing page"""
    return render_template('index.html')

@app.route('/teacher')
def teacher_portal():
    """Teacher dashboard"""
    return render_template('Teacher_potral.html')

@app.route('/teacher/create_exam')
def create_exam():
    """Create exam page"""
    return render_template('TP_create_exam.html')

@app.route('/teacher/submit_test', methods=['POST'])
def submit_test_details():
    """Submit new test"""
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
    """Paper checking page"""
    return render_template('start_paper_checking.html')

@app.route('/teacher/upload_and_check', methods=['POST'])
def upload_and_check():
    """Upload and check papers"""
    try:
        if not AI_ENABLED:
            return jsonify({
                "error": "AI not available. Steps to fix:\n1. Get API key from https://aistudio.google.com/app/apikey\n2. Update GOOGLE_API_KEY in app_fixed.py\n3. Restart app"
            }), 500
        
        if 'question_paper' not in request.files or 'answer_sheet' not in request.files:
            return jsonify({"error": "Both files required"}), 400
        
        question_paper = request.files['question_paper']
        answer_sheet = request.files['answer_sheet']
        
        if not question_paper.filename.endswith('.pdf') or not answer_sheet.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files allowed"}), 400
        
        qp_path = os.path.join(UPLOAD_FOLDER, f"qp_{uuid.uuid4().hex[:8]}.pdf")
        as_path = os.path.join(UPLOAD_FOLDER, f"as_{uuid.uuid4().hex[:8]}.pdf")
        
        question_paper.save(qp_path)
        answer_sheet.save(as_path)
        
        qp_text = read_pdf(qp_path)
        if not qp_text:
            return jsonify({"error": "Could not extract text from Question Paper"}), 500
        
        as_text = read_pdf(as_path)
        if not as_text:
            return jsonify({"error": "Could not extract text from Answer Sheet"}), 500
        
        try:
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""Question Paper:\n{qp_text}\n\nAnswer Sheet:\n{as_text}\n\nEvaluate comprehensively with marks and feedback."""
            
            response = model.generate_content(prompt)
            
            result_file = os.path.join(RESULTS_FOLDER, f"result_{uuid.uuid4().hex[:8]}.txt")
            with open(result_file, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            return jsonify({"success": True, "evaluation": response.text}), 200
            
        except Exception as api_error:
            if "API key not valid" in str(api_error):
                return jsonify({"error": "Invalid API Key. Get from: https://aistudio.google.com/app/apikey"}), 500
            return jsonify({"error": f"AI Error: {str(api_error)}"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/teacher/results')
def view_results():
    """View results"""
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
    """Student home"""
    return render_template('Student_test_check.html')

@app.route('/student/verify_code', methods=['POST'])
def verify_code():
    """Verify test code"""
    test_code = request.form['test_code']
    if is_code_valid(test_code):
        session['test_code'] = test_code
        return redirect(url_for('student_login'))
    return render_template('Student_test_check.html', error="Invalid test code")

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    """Student login"""
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
    """Test instructions"""
    if request.method == 'POST':
        return redirect(url_for('student_test_portal'))
    return render_template('Student_test_instruction.html')

@app.route('/student/test')
def student_test_portal():
    """Student test portal"""
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
    """Submit test"""
    return render_template('Student_test_submit.html')

# Add favicon route to prevent 404
@app.route('/favicon.ico')
def favicon():
    """Favicon"""
    return '', 204

if __name__ == '__main__':
    print("\n" + "="*60)
    print("DASH Application Starting...")
    print("="*60)
    print(f"AI Enabled: {'YES ✓' if AI_ENABLED else 'NO ✗'}")
    if not AI_ENABLED:
        print("\n⚠️  To enable AI:")
        print("1. Get key: https://aistudio.google.com/app/apikey")
        print("2. Update GOOGLE_API_KEY in app_fixed.py")
        print("3. Restart app")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, host='127.0.0.1')
