# app.py
from flask import Flask, Response, jsonify
from git import Repo
from omniccg import main

app = Flask(__name__)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/detect_clones")
def detect_clones():
    try:
        xml_obj = main() 
        return Response(xml_obj, status=200, mimetype="application/xml")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
