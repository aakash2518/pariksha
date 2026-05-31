try:
    from google import genai
except ImportError:
    import google.generativeai as genai
import PyPDF2
import json  # To work with JSON files
import os

def load_api_key(file_path):
    """Loads the API key from a JSON file."""

    try:
        with open(file_path, "r") as file:
            credentials = json.load(file)
        return credentials.get("private_key_id")  # Adjust key name if needed
    except FileNotFoundError:
        print(f"Error: API key file not found at {file_path}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        return None
    except Exception as e:
        print(f"An error occurred while loading API key: {e}")
        return None

def read_pdf(file_path):
    """Reads text from a PDF file."""

    text = ""
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() or ""
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")
    return text

def evaluate_pdfs_with_gemini(question_paper_path, answer_sheet_path, model):
    """Sends the content of two PDFs to Gemini for evaluation."""

    # Check if files exist
    if not os.path.exists(question_paper_path):
        return f"Error: Question paper file not found at {question_paper_path}"
    if not os.path.exists(answer_sheet_path):
        return f"Error: Answer sheet file not found at {answer_sheet_path}"

    print("\nReading PDFs...")
    question_paper_content = read_pdf(question_paper_path)
    answer_sheet_content = read_pdf(answer_sheet_path)

    if not question_paper_content:
        return "Error: Could not extract text from question paper PDF"
    if not answer_sheet_content:
        return "Error: Could not extract text from answer sheet PDF"

    prompt = f"Question Paper Content:\n{question_paper_content}\n\nAnswer Sheet Content:\n{answer_sheet_content}\n\nEvaluate the answer sheet based on the question paper. Provide a detailed report including marks for each question, overall marks, and constructive feedback."

    print("Sending to Gemini AI for evaluation...")
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error during evaluation: {e}"

def main():
    print("=== PDF Answer Sheet Evaluator ===\n")
    
    from dotenv import load_dotenv
    load_dotenv()
    GOOGLE_API_KEY = os.getenv("GEMINI_KEY_1", "")

    if not GOOGLE_API_KEY:
        print("Error: API key not set. Exiting.")
        return

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(model_name='gemini-2.0-flash')
        print("✓ Gemini AI initialized successfully\n")
    except Exception as e:
        print(f"Error initializing Gemini AI: {e}")
        return

    # User input for file paths
    question_paper_path = input("Enter the path to Question Paper PDF: ").strip().strip('"')
    answer_sheet_path = input("Enter the path to Answer Sheet PDF: ").strip().strip('"')

    evaluation_report = evaluate_pdfs_with_gemini(question_paper_path, answer_sheet_path, model)

    print("\n" + "="*50)
    print("--- Evaluation Report ---")
    print("="*50)
    print(evaluation_report)

if __name__ == "__main__":
    main()