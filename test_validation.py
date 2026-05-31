import pandas as pd

# Test the validation logic
TEST_DETAILS_CSV = r"Database\test_details.csv"

def is_code_valid(test_code):
    """Check if test code exists"""
    try:
        df = pd.read_csv(TEST_DETAILS_CSV)
        print(f"Columns in CSV: {df.columns.tolist()}")
        
        # Check both possible column names
        if 'unique code' in df.columns:
            result = test_code in df['unique code'].values
            print(f"Checking in 'unique code' column: {result}")
            return result
        elif 'Unique Test Code' in df.columns:
            result = test_code in df['Unique Test Code'].values
            print(f"Checking in 'Unique Test Code' column: {result}")
            return result
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# Test with a valid code from CSV
test_codes = ['283696b8', 'f0f35239', 'invalid123']

for code in test_codes:
    print(f"\nTesting code: {code}")
    result = is_code_valid(code)
    print(f"Result: {'Valid' if result else 'Invalid'}")
    print("-" * 50)
