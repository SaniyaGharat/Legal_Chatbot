# Indian Legal Assistant Chatbot

A high-performance, resilient web application designed to provide accurate information about Indian laws, resolve common legal procedural questions, and assist in drafting legal templates.

## ✨ Key Features

- **Multi-Model AI Gateway:** Implements a robust fallback chain starting with high-tier LLMs (like Claude 3.5 Sonnet and Gemini 1.5 Pro) and cascading down to ensure maximum uptime, even during rate limits or service interruptions.
- **Offline Intelligence & Lite-Extraction Engine:** If all AI APIs are unavailable, the assistant falls back to a specialized local knowledge base. It uses a custom regex-powered "Lite-Extraction" engine to automatically parse user messages for names, addresses, and monetary amounts to correctly fill legal templates seamlessly without an active internet connection.
- **Interactive Legal Templates:** Rapidly generate clean, fillable documents like Leave & License Agreements (Rent Agreements) or Legal Notices directly in the chat.
- **Modern "Fixed" UI Setup:** Built with a WhatsApp/ChatGPT-style interface. The text input remains fixed at the absolute bottom of the screen while conversation history and template sidebars scroll completely independently, ensuring you never lose your place.
- **Real-Time Procedural Guidance:** Accurately guides users on critical procedures, such as what steps to take if local police refuse to register an FIR, providing actionable steps under the CrPC and BNSS.

## 🚀 Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Optional: API keys from Anthropic (Claude) and Google (Gemini)

### Installation

1. Clone this repository
```bash
git clone https://github.com/yourusername/indian-legal-assistant.git
cd indian-legal-assistant
```

2. Create a virtual environment and activate it
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys
```bash
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

5. Run the application
```bash
python app.py
```

6. Open your browser and go to `http://127.0.0.1:5000`

## 📁 Project Structure

- `app.py` - Main Flask application containing the Multi-Model logic and Lite-Extraction engine.
- `templates/index.html` - Semantic HTML structure.
- `static/css/style.css` - Custom flexbox styling ensuring standard independent scrolling layout.
- `static/js/script.js` - Frontend logic for message rendering, history storage, and UI behavior.
- `conversations.json` - Local persistent storage for user chat history.

## ⚖️ Disclaimer

This tool is for informational and educational purposes only and does not constitute professional legal advice. Always consult with a qualified legal professional or advocate for advice directed towards specific legal situations.