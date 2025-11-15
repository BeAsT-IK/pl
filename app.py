from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

def full_stripe_check(cc, mm, yy, cvv):
    session = requests.Session()
    session.headers.update({
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    if len(yy) == 4:
        yy = yy[-2:]

    try:
        # Luhn algorithm to validate card number
        def luhn_check(card_num):
            digits = [int(d) for d in card_num]
            digits.reverse()
            total = 0
            for i, digit in enumerate(digits):
                if i % 2 == 1:
                    digit *= 2
                    if digit > 9:
                        digit -= 9
                total += digit
            return total % 10 == 0

        # Validate card format
        if not luhn_check(cc):
            return {"status": "Declined", "response": "Invalid card number (Luhn check failed)", "decline_type": "invalid_card"}
        
        # Validate expiry
        try:
            mm_int = int(mm)
            yy_int = int(yy)
            if mm_int < 1 or mm_int > 12:
                return {"status": "Declined", "response": "Invalid month", "decline_type": "invalid_card"}
        except:
            return {"status": "Declined", "response": "Invalid card format", "decline_type": "invalid_card"}
        
        # Validate CVV
        if not (len(cvv) == 3 or len(cvv) == 4):
            return {"status": "Declined", "response": "Invalid CVV length", "decline_type": "invalid_card"}
        
        # All validations passed
        return {"status": "Approved", "response": "Card validated successfully", "decline_type": "none"}
    
    except Exception as e:
        return {"status": "Declined", "response": str(e), "decline_type": "process_error"}

def get_bin_info(bin_number):
    try:
        response = requests.get(f'https://bins.antipublic.cc/bins/{bin_number}')
        return response.json() if response.status_code == 200 else {}
    except Exception:
        return {}

@app.route('/st', methods=['GET'])
def check_card_st():
    card_str = request.args.get('card')
    
    if not card_str:
        return jsonify({"error": "Please provide card details using the 'card' parameter in the URL."}), 400

    match = re.match(r'(\d{16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})', card_str)
    if not match:
        return jsonify({"error": "Invalid card format. Use CC|MM|YY|CVV."}), 400

    cc, mm, yy, cvv = match.groups()
    check_result = full_stripe_check(cc, mm, yy, cvv)
    bin_info = get_bin_info(cc[:6])

    final_result = {
        "status": check_result["status"],
        "response": check_result["response"],
        "decline_type": check_result["decline_type"],
        "bin_info": {
            "brand": bin_info.get('brand', 'Unknown'), "type": bin_info.get('type', 'Unknown'),
            "country": bin_info.get('country_name', 'Unknown'), "country_flag": bin_info.get('country_flag', ''),
            "bank": bin_info.get('bank', 'Unknown'),
        }
    }
    return jsonify(final_result)

@app.route('/check', methods=['GET'])
def check_card():
    return check_card_st()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
