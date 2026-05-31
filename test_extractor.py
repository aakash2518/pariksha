import sys; sys.path.insert(0, '.')
from app import extract_questions_from_pdf

# Test 1: single question 4 marks
t1 = "Q1. What is Python? (4 marks)"
r1 = extract_questions_from_pdf(t1)
print("Test 1:", r1)

# Test 2: multiple questions
t2 = """1. Explain photosynthesis. (5 marks)
2. What is Newton's law? (3 marks)
3. Define osmosis. (2 marks)"""
r2 = extract_questions_from_pdf(t2)
print("Test 2:", r2)

# Test 3: no marks shown
t3 = "Q1. What is AI?"
r3 = extract_questions_from_pdf(t3)
print("Test 3:", r3)
