#!/usr/bin/env python3
"""
Alternative AI Service - Use free AI APIs when Gemini quota is exhausted
"""

import requests
import json

def evaluate_with_huggingface(question_text, answer_text):
    """Use Hugging Face free API for evaluation"""
    try:
        # Hugging Face Inference API (Free)
        API_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
        
        prompt = f"""
        Question: {question_text[:500]}
        Student Answer: {answer_text[:500]}
        
        Please evaluate this answer and provide:
        1. Marks out of 10
        2. Brief feedback
        
        Format: MARKS: X/10, FEEDBACK: Your feedback here
        """
        
        response = requests.post(
            API_URL,
            headers={"Authorization": "Bearer hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"},  # Free tier
            json={"inputs": prompt}
        )
        
        if response.status_code == 200:
            result = response.json()
            return {"success": True, "evaluation": result[0]["generated_text"]}
        else:
            return {"success": False, "error": "Hugging Face API failed"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def evaluate_with_ollama_local(question_text, answer_text):
    """Use local Ollama if installed"""
    try:
        # Check if Ollama is running locally
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama2",
                "prompt": f"Evaluate this answer:\nQ: {question_text}\nA: {answer_text}\nProvide marks and feedback:",
                "stream": False
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return {"success": True, "evaluation": result["response"]}
        else:
            return {"success": False, "error": "Ollama not available"}
            
    except Exception as e:
        return {"success": False, "error": "Ollama not running"}

def evaluate_with_basic_algorithm(question_text, answer_text):
    """Basic keyword-based evaluation as last resort"""
    try:
        # Simple keyword matching algorithm
        question_words = set(question_text.lower().split())
        answer_words = set(answer_text.lower().split())
        
        # Calculate overlap
        common_words = question_words.intersection(answer_words)
        relevance_score = len(common_words) / len(question_words) if question_words else 0
        
        # Length factor
        length_factor = min(len(answer_text) / 100, 1.0)  # Normalize to 0-1
        
        # Calculate marks (0-10)
        marks = int((relevance_score * 0.7 + length_factor * 0.3) * 10)
        marks = max(1, min(marks, 10))  # Ensure 1-10 range
        
        feedback = f"Answer shows {relevance_score*100:.1f}% relevance to question. "
        if marks >= 8:
            feedback += "Excellent comprehensive answer."
        elif marks >= 6:
            feedback += "Good answer with room for improvement."
        elif marks >= 4:
            feedback += "Adequate answer but lacks detail."
        else:
            feedback += "Answer needs significant improvement."
        
        evaluation = f"MARKS: {marks}/10\nFEEDBACK: {feedback}"
        
        return {"success": True, "evaluation": evaluation, "ai_used": "Basic Algorithm"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def smart_evaluation_fallback(question_text, answer_text):
    """Try multiple AI services in order of preference"""
    
    print("🔄 Trying alternative AI services...")
    
    # Try Hugging Face first
    result = evaluate_with_huggingface(question_text, answer_text)
    if result["success"]:
        print("✅ Using Hugging Face AI")
        return result
    
    # Try local Ollama
    result = evaluate_with_ollama_local(question_text, answer_text)
    if result["success"]:
        print("✅ Using Local Ollama")
        return result
    
    # Fallback to basic algorithm
    print("⚠️ Using basic algorithm evaluation")
    return evaluate_with_basic_algorithm(question_text, answer_text)

if __name__ == "__main__":
    # Test the fallback system
    test_question = "What is the capital of France?"
    test_answer = "Paris is the capital city of France."
    
    result = smart_evaluation_fallback(test_question, test_answer)
    print("\n📝 Test Result:")
    print(result["evaluation"])