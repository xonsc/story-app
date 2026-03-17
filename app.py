from flask import Flask, jsonify, request
import requests, os

app = Flask(__name__)

IG_ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_ACCOUNT_ID   = os.environ.get("IG_ACCOUNT_ID", "26950760313")
DESIGN_ID       = os.environ.get("DESIGN_ID", "DAHCFrUWEbo")
CANVA_API_TOKEN = os.environ.get("CANVA_API_TOKEN", "")

@app.route("/")
def index():
    html = open("index.html").read()
    html = html.replace("__IG_ACCOUNT_ID__", IG_ACCOUNT_ID).replace("__DESIGN_ID__", DESIGN_ID)
    return html

@app.route("/api/refresh", methods=["POST"])
def refresh_pages():
    try:
        headers = {"Authorization": f"Bearer {CANVA_API_TOKEN}"}
        res = requests.get(
            f"https://api.canva.com/rest/v1/designs/{DESIGN_ID}/content/richtexts",
            headers=headers, timeout=30
        )
        if res.status_code != 200:
            return jsonify({"error": f"Canva API hatası: {res.status_code}"}), 400

        content_data = res.json()
        placeholder_kw = ["ürün ve fiyat", "rn ve fiyat", "urun ve fiyat"]
        header_texts = {"mavi", "zuccaciye", "home&kitchen", "home & kitchen", ""}
        product_pages = []

        for page in content_data.get("pages", []):
            page_num = page.get("index", 0)
            texts = []
            for element in page.get("elements", []):
                for tb in element.get("richtexts", []):
                    for para in tb.get("paragraphs", []):
                        for span in para.get("spans", []):
                            t = span.get("text", "").strip()
                            if t: texts.append(t)

            full_text = " ".join(texts).lower()
            is_placeholder = any(kw in full_text for kw in placeholder_kw)
            real_texts = [t for t in texts if t.lower() not in header_texts]

            if not is_placeholder and len(real_texts) >= 2:
                name, price = "", ""
                for t in real_texts:
                    if any(c.isdigit() for c in t) and ("TL" in t.upper() or "₺" in t):
                        price = t
                    elif len(t) > 3 and not name:
                        name = t
                product_pages.append({"pageNum": page_num, "name": name or f"Ürün {page_num}", "price": price or ""})

        if not product_pages:
            return jsonify({"error": "Dolu ürün sayfası bulunamadı"}), 404

        page_nums = [p["pageNum"] for p in product_pages]
        export_res = requests.post(
            "https://api.canva.com/rest/v1/exports",
            headers={**headers, "Content-Type": "application/json"},
            json={"design_id": DESIGN_ID, "format": {"type": "jpg", "quality": 100, "export_quality": "pro", "pages": page_nums}},
            timeout=60
        )
        urls = export_res.json().get("job", {}).get("urls", [])
        for i, page in enumerate(product_pages):
            page["exportUrl"] = urls[i] if i < len(urls) else ""

        return jsonify({"pages": product_pages, "count": len(product_pages)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/publish", methods=["POST"])
def publish_story():
    try:
        data = request.json
        export_url = data.get("exportUrl")
        ig_token = data.get("igToken") or IG_ACCESS_TOKEN
        ig_account = data.get("igAccountId") or IG_ACCOUNT_ID

        if not export_url: return jsonify({"error": "Export URL gerekli"}), 400
        if not ig_token or not ig_account: return jsonify({"error": "Instagram bilgileri eksik"}), 400

        c = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_account}/media",
            params={"image_url": export_url, "media_type": "STORIES", "access_token": ig_token},
            timeout=30
        ).json()
        if "error" in c: return jsonify({"error": c["error"]["message"]}), 400

        p = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_account}/media_publish",
            params={"creation_id": c["id"], "access_token": ig_token},
            timeout=30
        ).json()
        if "error" in p: return jsonify({"error": p["error"]["message"]}), 400

        return jsonify({"success": True, "id": p.get("id")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
