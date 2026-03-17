from flask import Flask, jsonify, request
import requests, os

app = Flask(__name__)

IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_ACCOUNT_ID   = os.environ.get("IG_ACCOUNT_ID", "26950760313")
DESIGN_ID       = os.environ.get("DESIGN_ID", "DAHCFrUWEbo")

PRODUCT_PAGES = [
    {"pageNum": 1, "name": "Korkmaz Stormia Kablosuz Dikey Süpürge", "price": "14000TL", "exportUrl": "https://export-download.canva.com/UWEbo/DAHCFrUWEbo/-1/0/0001-7202878939578491956.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAQYCGKMUH5AO7UJ26%2F20260317%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260317T082158Z&X-Amz-Expires=43112&X-Amz-Signature=7f49a561675b73c08de77fc57a172aef00fac401b802df95cce476866b8bd19f&X-Amz-SignedHeaders=host%3Bx-amz-expected-bucket-owner&response-expires=Tue%2C%2017%20Mar%202026%2020%3A20%3A30%20GMT"},
]

@app.route("/")
def index():
    html = open("index.html", encoding="utf-8").read()
    html = html.replace("__IG_ACCOUNT_ID__", IG_ACCOUNT_ID).replace("__DESIGN_ID__", DESIGN_ID)
    return html

@app.route("/api/refresh", methods=["POST"])
def refresh_pages():
    return jsonify({"pages": PRODUCT_PAGES, "count": len(PRODUCT_PAGES)})

@app.route("/api/publish", methods=["POST"])
def publish_story():
    try:
        data = request.json
        export_url = data.get("exportUrl")
        ig_token = data.get("igToken") or IG_ACCESS_TOKEN
        ig_account = data.get("igAccountId") or IG_ACCOUNT_ID

        if not export_url:
            return jsonify({"error": "Export URL gerekli"}), 400
        if not ig_token or not ig_account:
            return jsonify({"error": "Instagram bilgileri eksik"}), 400

        c = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_account}/media",
            params={"image_url": export_url, "media_type": "STORIES", "access_token": ig_token},
            timeout=30
        ).json()
        if "error" in c:
            return jsonify({"error": c["error"]["message"]}), 400

        p = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_account}/media_publish",
            params={"creation_id": c["id"], "access_token": ig_token},
            timeout=30
        ).json()
        if "error" in p:
            return jsonify({"error": p["error"]["message"]}), 400

        return jsonify({"success": True, "id": p.get("id")})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
