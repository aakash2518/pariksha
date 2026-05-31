#!/usr/bin/env python
"""Check all routes in the Flask app"""

print("="*60)
print("Checking Flask Routes")
print("="*60)
print()

try:
    from app import app
    
    print("✓ App imported successfully")
    print()
    print("Available Routes:")
    print("-"*60)
    
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': ','.join(rule.methods - {'HEAD', 'OPTIONS'}),
            'path': str(rule)
        })
    
    # Sort by path
    routes.sort(key=lambda x: x['path'])
    
    # Print routes
    for route in routes:
        print(f"{route['path']:40} [{route['methods']}]")
    
    print()
    print("="*60)
    print(f"Total routes: {len(routes)}")
    print("="*60)
    
    # Check specific route
    print()
    paper_checking_exists = any('/teacher/paper_checking' in r['path'] for r in routes)
    
    if paper_checking_exists:
        print("✓ /teacher/paper_checking route EXISTS")
        print()
        print("If you're getting 404:")
        print("1. Stop the app (Ctrl+C)")
        print("2. Run: python app.py")
        print("3. Refresh browser (Ctrl+F5)")
    else:
        print("✗ /teacher/paper_checking route MISSING")
        print()
        print("This route should exist. Check app.py file.")
    
except ImportError as e:
    print(f"✗ Error importing app: {e}")
    print()
    print("Make sure you're in the correct directory")
    print("and app.py exists")
except Exception as e:
    print(f"✗ Error: {e}")
