from flask import Flask, send_file

app = Flask(__name__)

@app.route('/teacher')
def teacher_portal():
    return send_file('teacher.py')

@app.route('/student')
def student_portal():
    return send_file('student.py')

if __name__ == '__main__':
    app.run(debug=True)
