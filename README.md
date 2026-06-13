GitRepo Explainer

AI-powered tool that explains any GitHub repository instantly. Paste a URL — get explanations, mind maps, slides, video scripts, and architecture diagrams.


⚙️ Setup

1. Install dependencies

bashpip install -r requirements.txt

2. Create a .env file

GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token

3. Run

bashpython app.py

Open http://localhost:5000 in your browser.


🚀 Features


📄 AI explanation of every source file
🧠 Mind maps
📊 Presentation slides
🎬 Video narration scripts
🎥 MP4 video generation
🖼️ Architecture diagrams
🌙 Dark / Light mode
📦 Bulk repo processing + fine-tuning dataset builder



🛠️ Tech Stack


Backend — Flask, Python
AI — LLaMA 3.3 70B via Groq (free)
Memory — ChromaDB + sentence-transformers (RAG)
Video — gTTS + Pillow + MoviePy



🔑 Get API Keys


Groq → console.groq.com (free)
GitHub → Settings → Developer Settings → Personal Access Tokens
