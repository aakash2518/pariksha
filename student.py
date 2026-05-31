from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import os
import csv

app = Flask(__name__, template_folder='UI/templates')
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# Folder path where the question CSV files are stored
questions_folder = r"Database\questions"

# CSV file path for test details
csv_file_path = r"Database\test_details.csv"
student_csv_file_path = r"Database\student_details.csv"

# Function to check if the test code exists in the CSV
def is_code_valid(test_code):
    try:
        df = pd.read_csv(csv_file_path)
        return test_code in df['unique code'].values
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return False

# Function to search and load test details based on test code
def get_test_details(test_code):
    test_details = {}
    try:
        with open(csv_file_path, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row['unique code'] == test_code:
                    test_details['name'] = row['name']
                    test_details['time'] = row['time']
                    test_details['date'] = row['date']
                    test_details['duration'] = row['duration']
                    test_details['subject'] = row['subject']
                    test_details['faculty '] = row.get('faculty ', 'N/A')
                    test_details['total  marks'] = row.get('total  marks', 'N/A')
                    break
    except Exception as e:
        print(f"Error fetching test details: {e}")
    return test_details

# Function to load questions based on test code
def load_questions(test_code):
    file_name = f"{test_code}_questions.csv"
    file_path = os.path.join(questions_folder, file_name)
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            return df[['Questions', 'Marks']].to_dict(orient='records')
        except Exception as e:
            print(f"Error reading the questions file: {e}")
            return None
    else:
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        test_code = request.form['test_code']
        if is_code_valid(test_code):
            session['test_code'] = test_code
            return redirect(url_for('student_login'))
        else:
            return render_template('Student_test_check.html', error="Enter a valid test code.")
    return render_template('Student_test_check.html')

@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        name = request.form['name']
        roll_number = request.form['roll_number']
        email = request.form['email']
        unique_code = session.get('test_code', None)

        try:
            with open(student_csv_file_path, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                if os.stat(student_csv_file_path).st_size == 0:
                    writer.writerow(['Name', 'Roll Number', 'Email ID', 'Unique Code'])
                writer.writerow([name, roll_number, email, unique_code])
        except Exception as e:
            print(f"Error saving student details: {e}")
        
        return redirect(url_for('test_instruction'))
    test_code = session.get('test_code', None)
    return render_template('Student_login_details.html', test_code=test_code)

@app.route('/test_instruction', methods=['GET', 'POST'])
def test_instruction():
    if request.method == 'POST':
        return redirect(url_for('student_test_portal', test_code=session.get('test_code')))
    return render_template('Student_test_instruction.html')

@app.route('/student_test_portal/<test_code>', methods=['GET'])
def student_test_portal(test_code):
    test_details = get_test_details(test_code)
    questions = load_questions(test_code)
    if test_details and questions:
        return render_template('Student_test_potral.html', test_details=test_details, questions=questions)
    else:
        return "Test details or questions not found"
@app.route('/submit', methods=['POST'])
def submit():
    # You can handle any form data here if needed
    return render_template('Student_test_submit.html')
if __name__ == '__main__':
    app.run(debug=True,port=8080)
