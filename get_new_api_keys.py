#!/usr/bin/env python3
"""
Quick Guide to Get New API Keys
"""

import webbrowser
import time

def open_api_key_pages():
    """Open multiple API key generation pages"""
    
    print("🚀 Opening API Key Generation Pages...")
    print("=" * 50)
    
    # List of services to get API keys from
    services = [
        {
            "name": "Google AI Studio (Gemini)",
            "url": "https://aistudio.google.com/app/apikey",
            "description": "Free tier: 60 requests/minute, 1500/day",
            "tip": "Use different Google accounts for multiple keys"
        },
        {
            "name": "xAI Console (Grok)",
            "url": "https://console.x.ai/",
            "description": "Paid service with high quality",
            "tip": "Add billing for immediate access"
        },
        {
            "name": "Hugging Face",
            "url": "https://huggingface.co/settings/tokens",
            "description": "Free inference API",
            "tip": "Good fallback option"
        }
    ]
    
    for i, service in enumerate(services, 1):
        print(f"\n{i}. {service['name']}")
        print(f"   📝 {service['description']}")
        print(f"   💡 {service['tip']}")
        print(f"   🔗 {service['url']}")
        
        try:
            webbrowser.open(service['url'])
            print(f"   ✅ Opened in browser")
        except:
            print(f"   ⚠️ Please manually open: {service['url']}")
        
        if i < len(services):
            print("   ⏳ Waiting 3 seconds before opening next...")
            time.sleep(3)
    
    print("\n" + "=" * 50)
    print("📋 INSTRUCTIONS:")
    print("1. Sign up/Login to each service")
    print("2. Generate API keys")
    print("3. Copy the keys")
    print("4. Add to app.py in API_KEYS list")
    
    print("\n🔧 How to add keys to app.py:")
    print("Replace this section in app.py:")
    print("""
API_KEYS = [
    "AIzaSy_YOUR_OLD_KEY_1_HERE",  # Old Key 1
    "AIzaSy_YOUR_OLD_KEY_2_HERE", # Old Key 2
    "AIzaSy_YOUR_OLD_KEY_3_HERE", # Old Key 3
]
""")
    
    print("\nWith your new keys:")
    print("""
API_KEYS = [
    "AIzaSy_YOUR_NEW_KEY_1_HERE",  # New Key 1
    "AIzaSy_YOUR_NEW_KEY_2_HERE",  # New Key 2
    "AIzaSy_YOUR_NEW_KEY_3_HERE",  # New Key 3
    "AIzaSy_YOUR_NEW_KEY_4_HERE",  # New Key 4
    "AIzaSy_YOUR_NEW_KEY_5_HERE",  # New Key 5
]
""")
    
    print("\n⚡ IMMEDIATE SOLUTIONS:")
    print("1. Wait 24 hours - quotas reset daily")
    print("2. Use different Google accounts")
    print("3. Try tomorrow morning")
    print("4. Add Grok credits for premium service")

def show_quota_info():
    """Show quota information"""
    print("\n📊 API QUOTA INFORMATION:")
    print("=" * 30)
    
    quotas = [
        {
            "service": "Google Gemini (Free)",
            "limits": "60 requests/minute, 1,500/day",
            "reset": "Daily at midnight PST",
            "cost": "Free"
        },
        {
            "service": "Google Gemini (Paid)",
            "limits": "1,000 requests/minute, unlimited/day",
            "reset": "Per minute",
            "cost": "$0.00025/1K tokens"
        },
        {
            "service": "xAI Grok",
            "limits": "Based on credits purchased",
            "reset": "Real-time billing",
            "cost": "$2-5 per 1M tokens"
        }
    ]
    
    for quota in quotas:
        print(f"\n🔹 {quota['service']}")
        print(f"   📈 Limits: {quota['limits']}")
        print(f"   🔄 Reset: {quota['reset']}")
        print(f"   💰 Cost: {quota['cost']}")

if __name__ == "__main__":
    print("🔑 API Key Generator & Quota Fix Tool")
    print("This will help you get new API keys to fix the quota issue")
    
    choice = input("\nWhat would you like to do?\n1. Open API key pages\n2. Show quota info\n3. Both\nChoice (1-3): ")
    
    if choice in ['1', '3']:
        open_api_key_pages()
    
    if choice in ['2', '3']:
        show_quota_info()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Get new API keys from the opened pages")
    print("2. Replace old keys in app.py")
    print("3. Test with: python fix_api_quota_issue.py")
    print("4. Run your app: python app.py")
    
    input("\nPress Enter to exit...")