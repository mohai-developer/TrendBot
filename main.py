# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime
from dotenv import load_dotenv
from trend_analysis import run_analysis
import anthropic

load_dotenv()

def generate_ai_summary(results):
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    stocks_data = ""
    for r in results:
        if "error" not in r:
            t = r["targets"]
            stocks_data += (
                r["ticker"] + ": "
                "السعر=" + str(r["price"]) + ", "
                "الاتجاه=" + r["direction"] + ", "
                "الخط=" + r["line_type"] + " (" + r["strength"] + ") عند " + str(r["line_val"]) + ", "
                "السحابة=" + r["cloud_phase"] + " " + r["cloud_color"] + ", "
                "الحجم=" + r["volume_status"] + ", "
                "SL=" + str(t["sl"]) + " TP1=" + str(t["tp1"]) + " TP2=" + str(t["tp2"]) + " TP3=" + str(t["tp3"]) + "\n"
            )

    prompt = """أنت محلل مالي محترف. لكل سهم في القائمة التالية اكتب جملة تحليلية واحدة سلسة وطبيعية تصف وضعه.
الجملة يجب أن تربط العوامل ببعض بشكل منطقي مثل:
"NVDA يتراجع نحو خط دعم قوي عند 118 في ظل استمرار السحابة الحمراء وحجم ضعيف، مما يرجح استمرار الضغط البيعي"

البيانات:
""" + stocks_data + """
اكتب الإجابة بهذا الشكل فقط:
TICKER: الجملة
TICKER: الجملة

لا تضف أي شيء آخر."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    summaries = {}
    for line in response.content[0].text.strip().split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            ticker = parts[0].strip()
            summary = parts[1].strip()
            summaries[ticker] = summary

    for r in results:
        if "error" not in r:
            r["summary"] = summaries.get(r["ticker"], r["ticker"] + " - لا يوجد تحليل")

    prompt2 = "في جملتين فقط، لخّص الوضع العام لهذه الأسهم بأسلوب محلل محترف:\n" + stocks_data
    response2 = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt2}]
    )
    return response2.content[0].text

def generate_html(results, ai_summary):
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    cards = ""
    for r in results:
        if "error" in r:
            cards += '<div class="card error"><h2>' + r["ticker"] + '</h2><p>خطأ في جلب البيانات</p></div>'
            continue

        is_bull     = "اخترق" in r["direction"] or "صعود" in r["direction"]
        card_class  = "bullish" if is_bull else "bearish"
        arrow       = "UP" if is_bull else "DN"
        cloud_dir   = "Green" if r["cloud_color"] == "خضراء" else "Red"
        badge_class = "strong" if r["strength"] == "قوي" else "weak"
        t           = r["targets"]

        cards += (
            '<div class="card ' + card_class + '">'

            # Header
            '<div class="card-header">'
            '<span class="ticker">' + r["ticker"] + '</span>'
            '<span class="price">$' + str(r["price"]) + '</span>'
            '<span class="arrow">' + arrow + '</span>'
            '</div>'
            '<div class="data-info">Data: ' + r["last_date"] + ' | ' + r["timeframe"] + '</div>'

            # AI Summary
         '<div class="summary">' + r.get("summary", r["direction"] + " - " + r["line_type"]) + '</div>'

            # Details
            '<div class="details">'
            '<div class="detail-item"><span class="label">الخط</span>'
            '<span class="value">' + r["direction"] + ' <span class="badge ' + badge_class + '">' + r["strength"] + '</span></span></div>'

            '<div class="detail-item"><span class="label">مستوى الخط</span>'
            '<span class="value">$' + str(r["line_val"]) + '</span></div>'

            '<div class="detail-item"><span class="label">السحابة [' + cloud_dir + ']</span>'
            '<span class="value">' + r["cloud_phase"] + ' ' + r["cloud_color"] + '</span></div>'

            '<div class="detail-item"><span class="label">الحجم</span>'
            '<span class="value">' + r["volume_status"] + '</span></div>'
            '</div>'

            # Targets
            '<div class="targets">'
            '<div class="target sl">SL: $' + str(t["sl"]) + '</div>'
            '<div class="target tp1">TP1: $' + str(t["tp1"]) + '</div>'
            '<div class="target tp2">TP2: $' + str(t["tp2"]) + '</div>'
            '<div class="target tp3">TP3: $' + str(t["tp3"]) + '</div>'
            '</div>'

            # Recommendation
            '<div class="recommendation">' + r["recommendation"] + '</div>'
            '</div>'
        )

    html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0d1117">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="TrendBot">
<title>TrendBot</title>
<link rel="manifest" href="/TrendBot/manifest.json">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh;padding:16px}
header{text-align:center;padding:24px 0 16px;border-bottom:1px solid #21262d;margin-bottom:20px}
header h1{font-size:1.6rem;color:#58a6ff}
header p{font-size:0.8rem;color:#8b949e;margin-top:4px}
.ai-summary{background:#161b22;border:1px solid #30363d;border-right:3px solid #58a6ff;border-radius:8px;padding:14px 16px;margin-bottom:20px;font-size:0.9rem;line-height:1.7;color:#c9d1d9}
.cards{display:flex;flex-direction:column;gap:14px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px;border-right:4px solid #30363d}
.card.bullish{border-right-color:#3fb950}
.card.bearish{border-right-color:#f85149}
.card.error{border-right-color:#8b949e;opacity:0.6}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.ticker{font-size:1.3rem;font-weight:700}
.price{font-size:1rem;color:#8b949e;font-weight:500}
.arrow{font-size:1rem;font-weight:700;padding:3px 10px;border-radius:6px;background:#0d1117}
.card.bullish .arrow{color:#3fb950}
.card.bearish .arrow{color:#f85149}
.data-info{font-size:0.72rem;color:#484f58;margin-bottom:10px}
.summary{font-size:0.88rem;line-height:1.7;color:#8b949e;margin-bottom:12px;padding:10px;background:#0d1117;border-radius:6px}
.details{display:flex;flex-direction:column;gap:6px;margin-bottom:12px}
.detail-item{display:flex;justify-content:space-between;font-size:0.82rem}
.label{color:#8b949e}
.value{color:#e6edf3;font-weight:500}
.badge{display:inline-block;padding:1px 7px;border-radius:10px;font-size:0.75rem;font-weight:600}
.badge.strong{background:#1f4a1f;color:#3fb950}
.badge.weak{background:#3a2a2a;color:#8b949e}
.targets{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}
.target{padding:4px 10px;border-radius:6px;font-size:0.78rem;font-weight:600}
.target.sl{background:#3a1a1a;color:#f85149}
.target.tp1{background:#1a2a1a;color:#3fb950}
.target.tp2{background:#1a2a1a;color:#3fb950;opacity:0.85}
.target.tp3{background:#1a2a1a;color:#3fb950;opacity:0.7}
.recommendation{font-size:0.85rem;color:#58a6ff;padding:8px 10px;background:#0d1117;border-radius:6px;font-weight:500}
footer{text-align:center;padding:24px 0 8px;font-size:0.75rem;color:#484f58}
</style>
</head>
<body>
<header>
  <h1>TrendBot</h1>
  <p>Last update: """ + now + """</p>
</header>
<div class="ai-summary">""" + ai_summary + """</div>
<div class="cards">""" + cards + """</div>
<footer>TrendBot - Auto updates hourly</footer>
<script>if("serviceWorker" in navigator){navigator.serviceWorker.register("sw.js")}</script>
</body>
</html>"""
    return html

def main():
    print("Analyzing stocks...")
    results = run_analysis()
    print("Analyzed: " + str(len(results)) + " stocks")
    try:
        ai_summary = generate_ai_summary(results)
        print("AI summary generated")
    except Exception as e:
        ai_summary = "AI summary unavailable."
        print("AI Error: " + str(e))
    html = generate_html(results, ai_summary)
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    with open("docs/report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Done - saved to docs/index.html")

if __name__ == "__main__":
    main()
