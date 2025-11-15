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
        # Direct call to Stripe with proper format
        stripe_data = {
            'card[number]': cc,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'card[cvc]': cvv,
        }
        
        # Add key properly
        stripe_data['key'] = 'pk_live_51Aa37vFDZqj3DJe6y08igZZ0Yu7eC5FPgGbh99Zhr7EpUkzc3QIlKMxH8ALkNdGCifqNy6MJQKdOcJz3x42XyMYK00mDeQgBuy'
        
        response = session.post('https://api.stripe.com/v1/tokens', data=stripe_data, timeout=15)
        response_json = response.json()
        
        # Success - card created token
        if response.status_code == 200 and response_json.get('id'):
            return {
                "status": "Approved",
                "response": f"Token created: {response_json.get('id')}",
                "decline_type": "none"
            }
        
        # Declined by Stripe
        if response.status_code == 402:
            error = response_json.get('error', {})
            return {
                "status": "Declined",
                "response": error.get('message', 'Card declined'),
                "decline_type": error.get('code', 'card_decline'),
                "error_type": error.get('type', 'card_error')
            }
        
        # Invalid request
        if response.status_code == 400:
            error = response_json.get('error', {})
            return {
                "status": "Declined",
                "response": error.get('message', 'Invalid request'),
                "decline_type": error.get('code', 'invalid_request_error'),
                "error_type": error.get('type', 'invalid_request_error')
            }
        
        # Any other error - return full Stripe response
        return {
            "status": "Declined",
            "response": response_json.get('error', {}).get('message', 'Unknown error'),
            "decline_type": response_json.get('error', {}).get('code', 'unknown'),
            "raw_response": response_json
        }
    
    except Exception as e:
        return {
            "status": "Declined",
            "response": str(e),
            "decline_type": "process_error"
        }

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
