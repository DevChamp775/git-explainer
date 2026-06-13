import requests
from rich.console import Console
import os
from dotenv import load_dotenv
load_dotenv()

console = Console(force_terminal=True)

# =====================================================
# CONFIGURATION
# =====================================================

# ── Ollama (local) ──
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_CHECK = "http://localhost:11434"
OLLAMA_MODEL = "deepseek-coder"

# ── Groq (cloud, free) ──
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")   # get free at console.groq.com
GROQ_MODEL   = "llama-3.3-70b-versatile"          # 70B model — much smarter than local

# ── Switch: True = use Groq cloud, False = use local Ollama ──
USE_GROQ = True


# =====================================================
# CONNECTION CHECK
# =====================================================

def check_ollama():
    """Returns True if Ollama is reachable, False otherwise."""
    if USE_GROQ:
        return True   # skip Ollama check when using Groq
    try:
        r = requests.get(OLLAMA_CHECK, timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# =====================================================
# GROQ GENERATOR
# =====================================================

def _generate_groq(prompt, status_msg):
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage

        with console.status(
            f"[bold yellow]{status_msg}[/]",
            spinner="dots"
        ):
            llm = ChatGroq(
                api_key=GROQ_API_KEY,
                model=GROQ_MODEL,
                max_tokens=4096
            )

            response = llm.invoke(
                [HumanMessage(content=prompt)]
            )

        return response.content.strip()

    except Exception as e:
        return f"[ERROR] Groq failed: {e}"


# =====================================================
# OLLAMA GENERATOR
# =====================================================

def _generate_ollama(prompt, status_msg):
    try:
        with console.status(
            f"[bold yellow]{status_msg}[/]",
            spinner="dots"
        ):
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model":  OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=300
            )

        if response.status_code != 200:
            return f"[ERROR] Ollama returned status {response.status_code}"

        return response.json().get("response", "").strip()

    except requests.exceptions.ConnectionError:
        return "[ERROR] Cannot connect to Ollama. Run: ollama serve"
    except requests.exceptions.Timeout:
        return "[ERROR] Timed out. Try a shorter snippet."
    except Exception as e:
        return f"[ERROR] {e}"


# =====================================================
# CORE GENERATOR — routes to Groq or Ollama
# =====================================================

def generate(prompt, status_msg="Thinking..."):
    if USE_GROQ:
        return _generate_groq(prompt, status_msg)
    else:
        return _generate_ollama(prompt, status_msg)


# =====================================================
# SAVE TO RAG + DATASET
# =====================================================

def _save_results(code, result, file_path, repo_url):
    """Save explanation to RAG memory and dataset."""

    # ── Save to RAG memory ──
    try:
        from rag_memory import save_explanation
        if file_path and result and not result.startswith("[ERROR]"):
            save_explanation(file_path, code, result)
    except Exception as e:
        console.print(f"[dim red]⚠ RAG save failed: {e}[/]")

    # ── Save to dataset ──
    try:
        from dataset_saver import save_example
        if result and not result.startswith("[ERROR]"):
            save_example(
                code,
                result,
                file_path=file_path,
                repo_url=repo_url
            )
    except Exception as e:
        console.print(f"[dim red]⚠ Dataset save failed: {e}[/]")


# =====================================================
# EXPLAIN A SINGLE FILE — RAG-POWERED
# =====================================================

def explain_file(code, file_path="", repo_url=""):
    """
    Explains a code file using Groq (cloud) or Ollama (local).
    Pulls similar past explanations from RAG memory as context.
    Saves result to RAG memory and dataset automatically.
    """

    # ── Pull similar past explanations from RAG memory ──
    context_block = ""
    try:
        from rag_memory import find_similar
        similar = find_similar(code)
        if similar:
            context_block  = "REFERENCE — similar code explained before:\n"
            context_block += "-" * 40 + "\n"
            for i, s in enumerate(similar, 1):
                context_block += f"[Reference {i}]\n{s[:600]}\n\n"
            context_block += "-" * 40 + "\n\n"
    except Exception:
        pass

    # ── Build the prompt ──
    prompt = f"""You are a world-class software engineer and technical writer.
Your job is to explain code files so clearly that even a beginner can understand,
while still being accurate enough for a senior developer.

{context_block}Analyze the code below and explain it under EXACTLY these headings.
Be specific — use the actual function names, variable names, and logic from the code.
Do NOT be generic. Every sentence should refer to something real in the code.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 🎯 PURPOSE
   What exactly does this file do?
   What problem does it solve?
   Where does it fit in a larger project?

2. 🔩 KEY COMPONENTS
   List every important function, class, and variable.
   For each one explain:
   - What it does
   - What inputs it takes
   - What it returns or changes

3. 📦 TECH & LIBRARIES
   Every import and why it is used.
   Any external APIs, databases, or services.
   What would break if you removed each one?

4. 🔄 STEP-BY-STEP FLOW
   Walk through exactly what happens when this code runs.
   Start from the entry point and trace every step.
   Use numbered steps.

5. ⚠️ IMPORTANT LOGIC & EDGE CASES
   Any clever algorithms, conditions, or patterns.
   What happens when something goes wrong?
   Any hardcoded values or assumptions worth noting?

6. 💡 BEGINNER SUMMARY
   Explain the whole file in 2–3 sentences.
   Use simple words. No jargon.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

--- CODE START ---
{code[:8000]}
--- CODE END ---
"""

    model_name = GROQ_MODEL if USE_GROQ else OLLAMA_MODEL
    result = generate(
        prompt,
        status_msg=f"{model_name} analyzing file..."
    )

    # ── Save to RAG + dataset ──
    _save_results(code, result, file_path, repo_url)

    return result


# =====================================================
# EXPLAIN A SINGLE FUNCTION
# =====================================================

def explain_function(code):
    prompt = f"""You are an expert software engineer.

Explain the following function in complete detail:

1. 🎯 PURPOSE
   What specific problem does this function solve?

2. 🔢 INPUTS & OUTPUTS
   Every parameter — name, type, what it means.
   Return value — type, what it contains, when it is None.

3. 🔄 STEP-BY-STEP LOGIC
   Walk through every line of logic in order.
   Explain every condition and loop.

4. 💥 EDGE CASES
   What happens with empty input?
   What exceptions can it raise?
   Any assumptions it makes about the input?

5. 📝 USAGE EXAMPLE
   Show a concrete example of calling this function.
   Show the expected output.

--- FUNCTION ---
{code}
--- END ---
"""
    model_name = GROQ_MODEL if USE_GROQ else OLLAMA_MODEL
    return generate(
        prompt,
        status_msg=f"{model_name} explaining function..."
    )


# =====================================================
# SUMMARIZE ENTIRE REPOSITORY
# =====================================================

def summarize_repo(all_code):
    prompt = f"""You are a senior software architect doing a full code review.

Analyze these code files from a GitHub repository and write a complete summary.
Be specific — use actual file names, function names, and variable names you see.
Do NOT be generic. Every point should reference something real in the code.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 🏷️ PROJECT NAME & PURPOSE
   What is this project?
   What exact problem does it solve?
   Who is the target user?

2. ⚡ MAIN FEATURES
   List every feature you can identify from the code.
   Be specific about what each feature does.

3. 🛠️ TECH STACK
   Every language, framework, library, and tool.
   Why each one is used.
   How they connect to each other.

4. 🏗️ ARCHITECTURE
   How are the files organized?
   Which file does what?
   How do they call each other?
   Draw a simple text diagram if helpful.

5. 🔄 DATA FLOW
   How does data enter the system?
   How is it processed?
   How does it exit or get stored?

6. 🌍 REAL-WORLD USE CASE
   Who would use this project?
   In what situation?
   What value does it provide?

7. 💡 BEGINNER SUMMARY
   Explain the whole project in 3 sentences.
   Use simple words a non-developer would understand.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

--- CODE SAMPLES ---
{all_code[:6000]}
--- END ---
"""
    model_name = GROQ_MODEL if USE_GROQ else OLLAMA_MODEL
    return generate(
        prompt,
        status_msg=f"{model_name} summarizing repository..."
    )