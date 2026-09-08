# TaskAnalyzer AI

## Run locally
1. Create a virtual environment:
   python -m venv .venv
2. Activate it (Windows):
   .venv\Scripts\activate
3. Install dependencies:
   pip install -r requirements.txt
4. Copy `.env.example` to `.env`.
5. Add your Gemini API key:
   GEMINI_API_KEY=your_key_here
6. Run:
   streamlit run app.py

## Notes
- The SQLite database is created automatically as `task_analyzer.db`.
- Never commit `.env` to GitHub.
- Conversation context is bounded to recent messages to reduce API usage.
- The app retries transient AI failures three times.
- For a public production app, replace SQLite with PostgreSQL and add server-side rate limiting, usage quotas, monitoring, and billing.
