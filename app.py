# app.py
from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

def luhn_check(card_num: str) -> bool:
    digits = [int(d) for d in card_num if d.isdigit()]
    digits.reverse()
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0

def get_bin_info(bin_number: str) -> dict:
    try:
        r = requests.get(f"https://bins.antipublic.cc/bins/{bin_number}", timeout=5)
        return r.json() if r.status_code == 200 else {}
    except:
        return {}

def full_stripe_check(cc: str, mm: str, yy: str, cvv: str) -> dict:
    try:
        # Luhn
        if not luhn_check(cc):
            return {"status": "Declined", "response": "Invalid card number (Luhn)", "decline_type": "invalid_card"}

        # Month
        try:
            month = int(mm)
            if not 1 <= month <= 12:
                return {"status": "Declined", "response": "Invalid month", "decline_type": "invalid_card"}
        except:
            return {"status": "Declined", "response": "Invalid month format", "decline_type": "invalid_card"}

        # Year
        try:
            int(yy)  # Just validate it's numeric
        except:
            return {"status": "Declined", "response": "Invalid year format", "decline_type": "invalid_card"}

        # CVV
        if len(cvv) not in (3, 4):
            return {"status": "Declined", "response": "Invalid CVV length", "decline_type": "invalid_card"}

        return {"status": "Approved", "response": "Card validated successfully", "decline_type": "none"}

    except Exception as e:
        return {"status": "Declined", "response": f"Error: {str(e)}", "decline_type": "process_error"}

# CORRECT WAY: Two separate route decorators
@app.route("/check", methods=["GET"])
@app.route("/st", methods=["GET"])
def check_card():
    card = request.args.get("card")
    if not card:
        return jsonify({"error": "Use ?card=CC|MM|YY|CVV"}), 400

    match = re.match(r"^(\d{15,16})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})$", card.strip())
    if not match:
        return jsonify({"error": "Format: 4111111111111111|01|26|123"}), 400

    cc, mm, yy, cvv = match.groups()
    result = full_stripe_check(cc, mm, yy, cvv)
    bin_info = get_bin_info(cc[:6])

    return jsonify({
        "status": result["status"],
        "response": result["response"],
        "decline_type": result["decline_type"],
        "bin_info": {
            "brand": bin_info.get("brand", "Unknown"),
            "type": bin_info.get("type", "Unknown"),
            "level": bin_info.get("level", "Unknown"),
            "country": bin_info.get("country_name", "Unknown"),
            "country_flag": bin_info.get("country_flag", ""),
            "bank": bin_info.get("bank", "Unknown"),
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
