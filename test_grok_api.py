#!/usr/bin/env python3
"""
Test script for Grok API integration
Run this to verify your Grok API key is working
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_grok_api():
    """Test Grok API connection and functionality"""
    
    print("🧪 Testing Grok API Integration...")
    print("=" * 50)
    
    # Test 1: Import libraries
    print("1. Testing imports...")
    try:
        from openai import OpenAI
        print("   ✅ OpenAI library imported successfully")
    except ImportError as e:
        print(f"   ❌ OpenAI library not found: {e}")
        print("   💡 Install with: pip install openai")
        return False
    
    # Test 2: Load API key from app.py
    print("\n2. Loading API key from app.py...")
    try:
        # Import the key from app.py
        from app import GROK_API_KEY, use_grok
        
        if GROK_API_KEY == "xai-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX":
            print("   ❌ Grok API key not set (still placeholder)")
            print("   💡 Add your real API key in app.py line ~60")
            return False
        elif not GROK_API_KEY.startswith("xai-"):
            print("   ❌ Invalid Grok API key format (should start with 'xai-')")
            return False
        else:
            print(f"   ✅ API key loaded: {GROK_API_KEY[:8]}...{GROK_API_KEY[-8:]}")
            
        if not use_grok:
            print("   ⚠️  Grok is disabled (use_grok = False)")
            print("   💡 Set use_grok = True in app.py to enable")
        else:
            print("   ✅ Grok is enabled")
            
    except Exception as e:
        print(f"   ❌ Error loading config: {e}")
        return False
    
    # Test 3: Test API connection
    print("\n3. Testing API connection...")
    try:
        client = OpenAI(
            api_key=GROK_API_KEY,
            base_url="https://api.x.ai/v1"
        )
        
        # Simple test prompt
        test_prompt = "Hello! Please respond with 'Grok API is working correctly' to confirm the connection."
        
        response = client.chat.completions.create(
            model="grok-2",
            messages=[{"role": "user", "content": test_prompt}],
            max_tokens=50
        )
        
        response_text = response.choices[0].message.content
        print(f"   ✅ API Response: {response_text}")
        
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ API connection failed: {error_msg}")
        
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            print("   💡 Invalid API key - check your key in console.x.ai")
        elif "429" in error_msg or "quota" in error_msg.lower():
            print("   💡 Quota exceeded - check your billing/limits")
        elif "404" in error_msg:
            print("   💡 Model not found - verify 'grok-2' is available")
        else:
            print("   💡 Check internet connection and xAI service status")
        
        return False
    
    # Test 4: Test evaluation functionality
    print("\n4. Testing evaluation functionality...")
    try:
        evaluation_prompt = """
Question: What is the capital of France?
Student Answer: Paris is the capital of France.

Evaluate this answer and provide:
MARKS: X/5
FEEDBACK: Brief feedback
"""
        
        response = client.chat.completions.create(
            model="grok-2",
            messages=[{"role": "user", "content": evaluation_prompt}],
            max_tokens=200
        )
        
        evaluation_result = response.choices[0].message.content
        print(f"   ✅ Evaluation test successful:")
        print(f"   📝 {evaluation_result[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Evaluation test failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed! Grok API is ready to use.")
    print("\n📋 Summary:")
    print("   ✅ OpenAI library installed")
    print("   ✅ API key configured")
    print("   ✅ Connection working")
    print("   ✅ Evaluation functionality working")
    
    if not use_grok:
        print("\n⚠️  Remember to set use_grok = True in app.py to enable Grok")
    
    return True

def test_fallback_system():
    """Test the fallback system (Grok -> Gemini)"""
    print("\n🔄 Testing Fallback System...")
    print("=" * 30)
    
    try:
        from app import evaluate_answer_sheets_with_ai
        
        # Test with sample data
        sample_question = "What is 2+2?"
        sample_answer = "2+2 equals 4"
        
        result = evaluate_answer_sheets_with_ai(sample_question, sample_answer)
        
        if result.get('success'):
            ai_used = result.get('ai_used', 'Unknown')
            print(f"   ✅ Evaluation successful with: {ai_used}")
            print(f"   📝 Result preview: {result['evaluation'][:100]}...")
        else:
            print(f"   ❌ Evaluation failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"   ❌ Fallback test failed: {e}")

if __name__ == "__main__":
    print("🚀 Starting Grok API Test Suite")
    print("This will test your Grok API integration\n")
    
    success = test_grok_api()
    
    if success:
        test_fallback_system()
        print("\n🎯 Ready to use! Start your Flask app with: python app.py")
    else:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        print("📖 Check GROK_API_SETUP_COMPLETE.md for detailed instructions")