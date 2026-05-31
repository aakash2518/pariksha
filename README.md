# 🎯 AI Answer Sheet Checker

An intelligent system for automatically evaluating answer sheets using advanced AI technology.

## ✨ Features

- 📄 **PDF Processing** - Extract text from question papers and answer sheets
- 🤖 **AI Evaluation** - Powered by Google Gemini AI and xAI Grok
- 👨‍🏫 **Teacher Portal** - Create exams, upload papers, view detailed results
- 👨‍🎓 **Student Portal** - Take tests and submit answers
- 📊 **Comprehensive Reports** - Detailed feedback with improvement suggestions
- 📱 **Responsive Design** - Works on desktop and mobile devices

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
Edit `app.py` and add your API keys:
```python
# Google Gemini AI API Keys
API_KEYS = [
    "AIzaSy_YOUR_GEMINI_KEY_1",
    "AIzaSy_YOUR_GEMINI_KEY_2",
    # Add more keys for better quota management
]

# Grok AI API Key (Optional)
GROK_API_KEY = "xai-YOUR_GROK_KEY"
use_grok = True  # Set to True to enable Grok
```

### 3. Run Application
```bash
python app.py
```

### 4. Access the System
- **Home**: http://localhost:5000
- **Teacher Portal**: http://localhost:5000/teacher
- **Student Portal**: http://localhost:5000/student

## 📋 How to Use

### For Teachers:
1. **Create Exam** - Set up questions and marking scheme
2. **Upload Papers** - Upload question paper and answer sheet PDFs
3. **AI Evaluation** - System automatically evaluates answers
4. **View Results** - Get detailed reports with feedback
5. **Download Reports** - Print or save evaluation reports

### For Students:
1. **Enter Test Code** - Use code provided by teacher
2. **Login** - Enter your details
3. **Take Test** - Answer questions online
4. **Submit** - Complete your test submission

## 🔧 API Keys Setup

### Google Gemini AI (Required)
1. Visit: https://aistudio.google.com/app/apikey
2. Create API key
3. Add to `API_KEYS` list in `app.py`

### xAI Grok (Optional)
1. Visit: https://console.x.ai/
2. Create API key
3. Add to `GROK_API_KEY` in `app.py`
4. Set `use_grok = True`

## 📁 Project Structure

```
AI-Answer-Sheet-Checker/
├── app.py                 # Main Flask application
├── student.py            # Student portal functionality
├── requirements.txt      # Python dependencies
├── UI/
│   ├── templates/       # HTML templates
│   └── static/         # CSS, JS, images
├── Database/
│   ├── questions/      # Question papers (CSV)
│   ├── uploads/        # Uploaded PDFs
│   ├── results/        # Evaluation results
│   └── *.csv          # Student and test data
└── Documentation/      # Setup guides and help
```

## 🧪 System Test

Run the system test to verify everything is working:
```bash
python test_system.py
```

## 🔍 Troubleshooting

### Common Issues:

**PDF Text Extraction Fails**
- Ensure PDFs contain text (not scanned images)
- Try different PDF files
- Check PDF is not corrupted

**API Quota Exceeded**
- Add more Gemini API keys
- Wait 24 hours for quota reset
- Consider upgrading to paid API plan

**Import Errors**
- Install dependencies: `pip install -r requirements.txt`
- Check Python version (3.8+ recommended)

## 📊 Technical Details

### AI Integration
- **Primary**: Google Gemini AI (multiple models)
- **Secondary**: xAI Grok (premium quality)
- **Fallback**: Basic algorithmic evaluation

### Evaluation Criteria
- **Content Accuracy** (60%) - Factual correctness
- **Understanding** (25%) - Conceptual grasp
- **Presentation** (15%) - Structure and clarity

### Supported Formats
- **Input**: PDF files (text-based)
- **Output**: HTML reports, CSV data
- **Export**: Print-to-PDF functionality

## 🎯 Production Ready

This system is production-ready with:
- ✅ Clean, optimized codebase
- ✅ Error handling and fallbacks
- ✅ Responsive web interface
- ✅ Comprehensive evaluation system
- ✅ Professional report generation

## 📞 Support

For setup help, check the documentation files:
- `QUICKSTART.md` - Quick setup guide
- `API_KEY_SETUP.md` - API configuration help
- `GROK_AI_SETUP.md` - Grok AI setup guide
- `PDF_TROUBLESHOOTING.md` - PDF processing help

---

**🎉 Ready to revolutionize answer sheet checking with AI!**