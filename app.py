import os
import time
import shutil
import json

from flask import (
    Flask, request,
    jsonify, Response, stream_with_context,
    send_file
)

from clone_repo import clone_repo, fetch_repository_info, get_headers
from file_extractor import get_code_files, get_important_files
from reader import read_file
from ai_explainer import explain_file, summarize_repo, check_ollama
from my_utils import short_path
from video_generator import generate_video_script, generate_full_video

import requests as req

app   = Flask(__name__)
store = {}   # in-memory store: session_id → data

COLORS = {
    "JavaScript": "#f7df1e", "Python":     "#3572A5",
    "HTML":       "#e34c26", "CSS":        "#563d7c",
    "TypeScript": "#2b7489", "Java":       "#b07219",
    "C++":        "#f34b7d", "Go":         "#00ADD8",
    "Rust":       "#dea584", "Julia":      "#a270ba",
    "Ruby":       "#701516", "PHP":        "#4F5D95",
    "Shell":      "#89e051", "Kotlin":     "#F18E33",
    "Swift":      "#ffac45", "Vue":        "#41b883",
}

CODE_PREVIEW  = 5000
EXPLAIN_LIMIT = 8000


# ── helpers ──────────────────────────────────────

def get_language_data(repo_info):
    try:
        r     = req.get(repo_info["languages_url"], headers=get_headers(), timeout=10)
        langs = r.json()
        total = sum(langs.values())
        return [
            {
                "name":  lang,
                "pct":   round((b / total) * 100, 1),
                "color": COLORS.get(lang, "#8b8b8b")
            }
            for lang, b in sorted(langs.items(), key=lambda x: -x[1])
        ]
    except Exception:
        return []


def sse(event, data):
    return f"data: {json.dumps({'event': event, 'data': data})}\n\n"


# ── routes ───────────────────────────────────────

@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    url = request.json.get("url", "").strip().rstrip("/")
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    if not check_ollama():
        return jsonify({"error": "AI service not available. Check your Groq API key."}), 503

    repo_info = fetch_repository_info(url)
    if not repo_info:
        return jsonify({"error": "Repository not found."}), 404

    return jsonify({
        "name":        repo_info.get("name", ""),
        "owner":       repo_info["owner"]["login"],
        "stars":       repo_info.get("stargazers_count", 0),
        "forks":       repo_info.get("forks_count", 0),
        "language":    repo_info.get("language", "Unknown"),
        "description": repo_info.get("description") or "No description",
        "url":         url,
        "languages":   get_language_data(repo_info),
        "repo_url":    repo_info.get("html_url", url),
    })


@app.route("/api/explain")
def explain_stream():
    url = request.args.get("url", "").strip().rstrip("/")
    if not url:
        return jsonify({"error": "No URL"}), 400

    def generate():
        repo_path = None
        try:
            yield sse("status", "Cloning repository...")
            repo_path = clone_repo(url)
            if not repo_path:
                yield sse("error", "Failed to clone repository.")
                return

            yield sse("status", "Extracting source files...")
            all_files = get_code_files(repo_path)
            if not all_files:
                yield sse("error", "No supported source files found.")
                return

            if len(all_files) > 100:
                max_f = 20
            elif len(all_files) > 50:
                max_f = 15
            else:
                max_f = 10

            selected   = get_important_files(all_files, max_f)
            file_names = [short_path(f) for f in selected]
            yield sse("files", file_names)

            yield sse("status", "Preparing code for summary...")
            combined = ""
            for f in selected:
                code = read_file(f)
                if not code.strip():
                    continue
                combined += f"\n\n### FILE: {short_path(f)}\n{code[:CODE_PREVIEW]}\n"

            yield sse("status", "Generating repository summary...")
            summary = summarize_repo(combined)
            yield sse("summary", summary)

            repo_name   = url.rstrip("/").split("/")[-1]
            explanations = []

            for idx, f in enumerate(selected):
                code = read_file(f)
                if not code.strip():
                    continue
                fname = short_path(f)
                yield sse("explaining", f"({idx+1}/{len(selected)}) {fname}")
                exp = explain_file(code[:EXPLAIN_LIMIT], file_path=f, repo_url=url)
                explanations.append({"file": fname, "explanation": exp})
                yield sse("explanation", {
                    "file":        fname,
                    "explanation": exp,
                    "index":       idx + 1,
                    "total":       len(selected)
                })

            # Store for video generation
            session_id = str(int(time.time()))
            store[session_id] = {
                "repo_name":    repo_name,
                "repo_url":     url,
                "summary":      summary,
                "explanations": explanations
            }
            yield sse("session", session_id)
            yield sse("done", "Analysis complete!")

        except Exception as e:
            yield sse("error", str(e))
        finally:
            if repo_path:
                shutil.rmtree(repo_path, ignore_errors=True)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/api/generate-script", methods=["POST"])
def gen_script():
    data       = request.json
    session_id = data.get("session_id", "")
    file_index = data.get("file_index", 0)

    if session_id not in store:
        return jsonify({"error": "Session not found"}), 404

    session     = store[session_id]
    explanations = session["explanations"]

    if file_index >= len(explanations):
        return jsonify({"error": "File index out of range"}), 400

    entry     = explanations[file_index]
    repo_name = session["repo_name"]

    script = generate_video_script(
        entry["file"],
        entry["explanation"],
        repo_name
    )

    return jsonify({
        "file":   entry["file"],
        "script": script
    })


@app.route("/api/generate-video", methods=["POST"])
def gen_video():
    data       = request.json
    session_id = data.get("session_id", "")
    file_index = data.get("file_index", 0)

    if session_id not in store:
        return jsonify({"error": "Session not found"}), 404

    session      = store[session_id]
    explanations = session["explanations"]

    if file_index >= len(explanations):
        return jsonify({"error": "File index out of range"}), 400

    entry  = explanations[file_index]
    result = generate_full_video(
        entry["file"],
        entry["explanation"],
        session["repo_name"]
    )

    if result["status"] == "done" and result["video_path"]:
        return jsonify({
            "status":     "done",
            "video_path": result["video_path"],
            "script":     result["script"]
        })
    else:
        return jsonify({
            "status":  result["status"],
            "script":  result.get("script", ""),
            "message": "Video generation failed at: " + result["status"]
        })


@app.route("/api/download-video")
def download_video():
    path = request.args.get("path", "")
    if not path or not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_file(path, as_attachment=True)


@app.route("/api/db-stats")
def db_stats():
    try:
        from rag_memory import get_memory_size
        rag = get_memory_size()
    except Exception:
        rag = 0
    try:
        from dataset_saver import get_count
        dataset = get_count()
    except Exception:
        dataset = 0
    return jsonify({
        "rag_entries":      rag,
        "dataset_examples": dataset,
        "fine_tune_ready":  dataset >= 500
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)