# app.py
from flask import Flask, Response, request
from flask_cors import CORS
from omniccg import main

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/detect_clones")
def detect_clones():
    general_settings = request.get_json(silent=True)
    xml_obj = main(general_settings) 
    return Response(xml_obj, status=200, mimetype="application/xml")

if __name__ == "__main__":
    # https://chatgpt.com/share/690d2d88-8e70-800d-b9c1-052e508baf89
    app.run(host="127.0.0.1", port=5000, debug=True)

