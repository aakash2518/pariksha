import PyPDF2
import sys

def test_pdf(file_path):
    """Test if PDF can be read"""
    print(f"\n{'='*60}")
    print(f"Testing PDF: {file_path}")
    print(f"{'='*60}\n")
    
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            
            print(f"✓ PDF opened successfully")
            print(f"  Number of pages: {len(reader.pages)}")
            
            if len(reader.pages) == 0:
                print("✗ ERROR: PDF has no pages!")
                return False
            
            # Try to extract text from first page
            first_page = reader.pages[0]
            text = first_page.extract_text()
            
            if text and text.strip():
                print(f"✓ Text extraction successful")
                print(f"  Characters extracted: {len(text)}")
                print(f"\n  First 200 characters:")
                print(f"  {'-'*60}")
                print(f"  {text[:200]}")
                print(f"  {'-'*60}\n")
                return True
            else:
                print("✗ ERROR: No text could be extracted!")
                print("  This might be a scanned image PDF.")
                print("  You need OCR (Optical Character Recognition) to read this PDF.")
                print("\n  Solutions:")
                print("  1. Use a text-based PDF instead of scanned images")
                print("  2. Install pytesseract for OCR: pip install pytesseract")
                print("  3. Use online OCR tools to convert the PDF first")
                return False
                
    except FileNotFoundError:
        print(f"✗ ERROR: File not found: {file_path}")
        return False
    except Exception as e:
        print(f"✗ ERROR: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Test provided file
        test_pdf(sys.argv[1])
    else:
        print("Usage: python test_pdf_reader.py <path_to_pdf>")
        print("\nExample:")
        print("  python test_pdf_reader.py question_paper.pdf")
