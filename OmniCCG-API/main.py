from flask_cors import CORS
from core import execute_omniccg
import subprocess
from flask import Flask, Response, request, jsonify
from get_code_snippets import _ensure_repo, _checkout, _safe_repo_path, _slice_lines, _read_text_with_fallback
from pathlib import Path

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/detect_clones")
def detect_clones():
    general_settings = request.get_json(silent=True)
    xml_obj, _, _  = execute_omniccg(general_settings) 
    return Response(xml_obj, status=200, mimetype="application/xml")

@app.post("/get_code_snippets")
def snippets():
    payload = request.get_json(silent=True) or {}
    git_url = payload.get("git_url", "")
    commit = payload.get("commit", "")
    sources = payload.get("sources") or payload.get("items") or []

    if not git_url or not commit or not isinstance(sources, list):
        return jsonify({
            "error": "Missing or invalid fields. Required: git_url (str), commit (str), sources (list)."
        }), 400

    try:
        repo_dir = _ensure_repo(git_url)
        _checkout(repo_dir, commit)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Git operation failed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    results = []
    for src in sources:
        fpath = src.get("file") or src.get("path")
        startline = src.get("startline") or src.get("start") or src.get("ls")
        endline = src.get("endline") or src.get("end") or src.get("le")

        item = {
            "file": fpath,
            "startline": startline,
            "endline": endline,
        }

        if not fpath or startline is None or endline is None:
            item["error"] = "Invalid item. Required keys: file, startline, endline."
            results.append(item)
            continue

        try:
            abs_path = _safe_repo_path(repo_dir, fpath)
            text = _read_text_with_fallback(str(abs_path))
            snippet = _slice_lines(text, int(startline), int(endline))
            item["content"] = snippet
        except Exception as e:
            item["error"] = f"{type(e).__name__}: {e}"

        results.append(item)

    return jsonify({
        "repo_dir": repo_dir,
        "commit": commit,
        "count": len(results),
        "snippets": results
    }), 200

@app.post("/get_metrics")
def get_metrics():
    payload = request.get_json(silent=True) or {}
    git_url = payload.get("git_url", "")
    project = git_url.split('/')[-1]
    base_dir = Path.cwd() / "cloned_repositories" / project
    metrics_path = (base_dir / "metrics.xml").resolve()
    xml_result = open(metrics_path, 'r').read()
    
    return Response(xml_result, status=200, mimetype="application/xml")


if __name__ == "__main__":
    # https://chatgpt.com/share/690d2d88-8e70-800d-b9c1-052e508baf89
    app.run(host="127.0.0.1", port=5000, debug=True)

