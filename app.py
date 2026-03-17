from flask import Flask, jsonify, request
import requests, os, json

app = Flask(__name__)

IG_ACCESS_TOKEN   = os.environ.get("IG_ACCESS_TOKEN", "")
IG_ACCOUNT_ID     = os.environ.get("IG_ACCOUNT_ID", "26950760313")
DESIGN_ID         = os.environ.get("DESIGN_ID", "DAHCFrUWEbo")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

@app.route("/")
def index():
    html = open("index.html", encoding="utf-8").read()
    html = html.replace("__IG_ACCOUNT_ID__", IG_ACCOUNT_ID).replace("__DESIGN_ID__", DESIGN_ID)
    return html

@app.route("/api/refresh", methods=["POST"])
def refresh_pages():
    try:
        prompt = f"""Sen bir Canva otomasyon asistanısın.

Design ID: {DESIGN_ID}

1. get-design-content aracıyla tüm sayfaların metin içeriğini oku
2. "rn ve Fiyat" veya "ürün ve Fiyat" gibi placeholder içeren sayfaları HARIÇ tut
3. Gerçek ürün adı ve fiyat içeren sayfaları belirle
4. O sayfaları export-design aracıyla JPG formatında, quality:100, export_quality:"pro" olarak export et
5. Sonucu SADECE şu JSON formatında ver, başka hiçbir şey yazma:

{{"pages":[{{"pageNum":1,"name":"Ürün Adı","price":"275TL","exportUrl":"https://..."}}]}}"""

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2000,
                "mcp_servers": [{
                    "type": "url",
                    "url": "https://mcp.canva.com/mcp",
                    "name": "canva-mcp"
                }],
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=120
        )

        data = response.json()

        # Text bloklarından JSON'u çıkar
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        # JSON parse et
        import re
        match = re.search(r'\{[\s\S]*\}', text)
        if not match:
            return jsonify({"error": "Canva yanıtı ayrıştırılamadı: " + text[:200]}), 500

        result = json.loads(match.group(0))
        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/publish", methods=["POST"])
def publish_story():
    try:
        data = request.json
        export_url = data.get("exportUrl")
        ig_token   = data.get("igToken") or IG_ACCESS_TOKEN
        ig_account = data.get("igAccountId") or IG_ACCOUNT_ID

        if not export_url:
            return jsonify({"error": "Export URL gerekli"}), 400
        if not ig_token or not ig_account:
            return jsonify({"error": "Instagram bilgileri eksik"}), 400

        # Container oluştur
        c = requests.post(
            f"https://graph.facebook.com/v19.0/{ig_account}/media",
            params={"image_url": export_url, "media_type": "STORIES", "access_token": ig_token},
            timeout=30
        ).json()
        if "error" in c:
            return jsonify({"error": c["error"]["message"]}), 400

        # Yayınla
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
