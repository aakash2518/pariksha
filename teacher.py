from flask import Flask, request, render_template, jsonify
import csv
import uuid
import os
import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

# Try to import AI libraries - make them optional
try:
    import google.generativeai as genai
    AI_ENABLED = True
    print("✓ Google Generative AI loaded successfully")
except ImportError as e:
    AI_ENABLED = False
    print(f"⚠ Warning: Google Generative AI not available")
    print("  Paper checking feature will be disabled.")

try:
    from openai import OpenAI
    GROK_ENABLED = True
    print("✓ OpenAI (for Grok) loaded successfully")
except ImportError as e:
    GROK_ENABLED = False
    print(f"⚠ Warning: OpenAI library not available for Grok")

import PyPDF2

# Specify the path to the templates folder
app = Flask(__name__, template_folder='UI/templates')

# Ensure directories exist to store questions files
QUESTIONS_DIR = r'Database\questions'
UPLOAD_FOLDER = r'Database\uploads'
os.makedirs(QUESTIONS_DIR, exist_ok=True)
os.makedirs(r'Database', exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# API Keys
from dotenv import load_dotenv
load_dotenv()
GOOGLE_API_KEY = os.getenv("GEMINI_KEY_1", "")
GROK_API_KEY = os.getenv("GROK_API_KEY", "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
USE_GROK = True

@app.route('/')
def teacher_portal():
    return render_template('Teacher_potral.html')

# PDF Reading Function
def read_pdf(file_path):
    """Reads text from a PDF file."""
    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() or ""
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

# Evaluate PDFs with AI (Grok with Gemini fallback)
def evaluate_pdfs(question_paper_path, answer_sheet_path):
    """Sends the content of two PDFs to AI for evaluation."""
    
    if not os.path.exists(question_paper_path):
        return {"error": f"Question paper file not found at {question_paper_path}"}
    if not os.path.exists(answer_sheet_path):
        return {"error": f"Answer sheet file not found at {answer_sheet_path}"}

    question_paper_content = read_pdf(question_paper_path)
    answer_sheet_content = read_pdf(answer_sheet_path)

    if not question_paper_content:
        return {"error": "Could not extract text from question paper PDF"}
    if not answer_sheet_content:
        return {"error": "Could not extract text from answer sheet PDF"}

    prompt = f"""Question Paper Content:
{question_paper_content}

Answer Sheet Content:
{answer_sheet_content}

Evaluate the answer sheet based on the question paper. Provide a detailed report including:
1. Marks for each question
2. Overall marks obtained
3. Constructive feedback
4. Areas of improvement"""

    # Try Grok First
    if USE_GROK and GROK_ENABLED and GROK_API_KEY != "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX":
        try:
            print("Evaluating with Grok AI...")
            client = OpenAI(
                api_key=GROK_API_KEY,
                base_url="https://api.x.ai/v1"
            )
            response = client.chat.completions.create(
                model="grok-beta",
                messages=[{"role": "user", "content": prompt}]
            )
            print("✓ Evaluation complete with Grok AI")
            return {"success": True, "evaluation": response.choices[0].message.content}
        except Exception as e:
            print(f"Grok evaluation failed, falling back to Gemini: {str(e)}")

    # Fallback to Gemini
    try:
        print("Evaluating with Gemini AI...")
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(model_name='gemini-2.0-flash')
        
        response = model.generate_content(prompt)
        print("✓ Evaluation complete with Gemini AI")
        return {"success": True, "evaluation": response.text}
    except Exception as e:
        return {"error": f"Error during evaluation (both APIs failed): {str(e)}"}

# Route for paper checking page
@app.route('/start_paper_checking')
def start_paper_checking():
    return render_template('start_paper_checking.html')

# Route for rendering the HTML form
@app.route('/TP_create_exam')
def index():
    return render_template('TP_create_exam.html')  # This will look for TP_create_exam.html in the UI/templates folder

# Route for handling form submission and saving to CSV files
@app.route('/submit_test_details', methods=['POST'])
def submit_test_details():
    name = request.form['name']
    time = request.form['time']
    date = request.form['date']
    duration = request.form['duration']
    subject = request.form['subject']
    faculty = request.form['faculty']
    total_marks = request.form['total_marks']

    # Get multiple questions and marks from the form
    questions = request.form.getlist('questions')
    marks = request.form.getlist('marks')

    # Generate unique test code using UUID
    unique_test_code = str(uuid.uuid4())[:8]

    # Save exam details to a single CSV file
    exam_file_path = r"Database\test_details.csv"
    with open(exam_file_path, 'a', newline='') as exam_file:  # Append mode
        writer = csv.writer(exam_file)
        # Write the header only if the file is empty
        if os.stat(exam_file_path).st_size == 0:
            writer.writerow(["Name", "Time", "Date", "Duration", "Subject", "Faculty Name", "Total Marks", "Unique Test Code"])
        # Write the test details
        writer.writerow([name, time, date, duration, subject, faculty, total_marks, unique_test_code])

    # Create the questions and marks CSV file
    questions_file_path = os.path.join(QUESTIONS_DIR, f"{unique_test_code}_questions.csv")
    with open(questions_file_path, 'w', newline='') as questions_file:
        writer = csv.writer(questions_file)
        # Write questions and marks
        writer.writerow(["Questions", "Marks"])
        for q, m in zip(questions, marks):
            writer.writerow([q, m])

    return render_template('success.html', test_code=unique_test_code)

# Route for uploading and checking papers
@app.route('/upload_and_check', methods=['POST'])
def upload_and_check():
    try:
        # Check if files are present
        if 'question_paper' not in request.files or 'answer_sheet' not in request.files:
            return jsonify({"error": "Both question paper and answer sheet are required"}), 400
        
        question_paper = request.files['question_paper']
        answer_sheet = request.files['answer_sheet']
        
        # Check if files are PDFs
        if not question_paper.filename.endswith('.pdf') or not answer_sheet.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files are allowed"}), 400
        
        # Save uploaded files
        question_paper_path = os.path.join(app.config['UPLOAD_FOLDER'], f"qp_{uuid.uuid4().hex[:8]}.pdf")
        answer_sheet_path = os.path.join(app.config['UPLOAD_FOLDER'], f"as_{uuid.uuid4().hex[:8]}.pdf")
        
        question_paper.save(question_paper_path)
        answer_sheet.save(answer_sheet_path)
        
        # Evaluate the papers
        result = evaluate_pdfs(question_paper_path, answer_sheet_path)
        
        # Clean up uploaded files (optional)
        # os.remove(question_paper_path)
        # os.remove(answer_sheet_path)
        
        if "error" in result:
            return jsonify(result), 500
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
