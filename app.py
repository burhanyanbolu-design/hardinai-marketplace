"""
Hardin AI Marketplace — Payment Backend
Handles Stripe payments, file delivery, and tip/donations
"""

import os
import json
import stripe
from flask import Flask, request, jsonify, redirect, send_file
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLIC_KEY = os.getenv('STRIPE_PUBLIC_KEY')
DOMAIN = os.getenv('MARKETPLACE_DOMAIN', 'https://marketplace.hardinai.co.uk')

# ── Product catalogue ─────────────────────────────────────────────────────────
# In production this would be a database
PRODUCTS = {
    'prod_001': {
        'name': 'GPT Customer Support Bot',
        'description': 'Fully trained chatbot for e-commerce customer support.',
        'price': 2900,  # pence
        'category': 'AI Chatbots',
        'file': 'files/gpt-support-bot.zip',
        'seller_id': 'seller_001',
    },
    'prod_002': {
        'name': 'Stock Trading Signal Bot',
        'description': 'Python trading bot with RSI, MACD and EMA signals.',
        'price': 4900,
        'category': 'Trading Bots',
        'file': 'files/trading-signal-bot.zip',
        'seller_id': 'seller_002',
    },
    'prod_003': {
        'name': 'LinkedIn Automation Script',
        'description': 'Automate connection requests and follow-ups.',
        'price': 1900,
        'category': 'Automation',
        'file': 'files/linkedin-automation.zip',
        'seller_id': 'seller_003',
    },
    'prod_004': {
        'name': 'ChatGPT Prompt Pack (500 Prompts)',
        'description': '500 tested prompts for marketing, coding and business.',
        'price': 900,
        'category': 'Prompt Packs',
        'file': 'files/prompt-pack-500.zip',
        'seller_id': 'seller_004',
    },
    'prod_005': {
        'name': 'Invoice Generator AI',
        'description': 'Auto-generate professional invoices from text input.',
        'price': 1500,
        'category': 'Automation',
        'file': 'files/invoice-generator.zip',
        'seller_id': 'seller_005',
    },
    'prod_006': {
        'name': 'SEO Content Bot',
        'description': 'Generate SEO-optimised blog posts automatically.',
        'price': 3500,
        'category': 'AI Templates',
        'file': 'files/seo-content-bot.zip',
        'seller_id': 'seller_006',
    },
}

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/products')
def get_products():
    """Return all verified products"""
    products = []
    for pid, p in PRODUCTS.items():
        products.append({
            'id': pid,
            'name': p['name'],
            'description': p['description'],
            'price': p['price'] / 100,
            'price_display': f"£{p['price']/100:.0f}",
            'category': p['category'],
        })
    return jsonify(products)

@app.route('/api/checkout/<product_id>', methods=['POST'])
def create_checkout(product_id):
    """Create Stripe checkout session for a product"""
    product = PRODUCTS.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': product['name'],
                        'description': product['description'],
                    },
                    'unit_amount': product['price'],
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}&product={product_id}",
            cancel_url=f"{DOMAIN}/cancel",
            metadata={
                'product_id': product_id,
                'product_name': product['name'],
            }
        )
        return jsonify({'checkout_url': session.url, 'session_id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tip', methods=['POST'])
def create_tip():
    """Create Stripe checkout for a tip/donation"""
    data = request.json or {}
    amount = int(data.get('amount', 5)) * 100  # convert to pence

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'gbp',
                    'product_data': {
                        'name': 'Support Hardin AI Marketplace',
                        'description': 'Thank you for supporting the marketplace!',
                    },
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{DOMAIN}/tip-thanks",
            cancel_url=f"{DOMAIN}",
        )
        return jsonify({'checkout_url': session.url})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/success')
def success():
    """Handle successful payment — deliver file"""
    session_id = request.args.get('session_id')
    product_id = request.args.get('product')

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            product = PRODUCTS.get(product_id)
            if product:
                # Log the sale
                _log_sale(session, product_id, product)
                # Serve success page with download
                return f"""
                <!DOCTYPE html>
                <html>
                <head>
                  <title>Payment Successful — Hardin AI Marketplace</title>
                  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
                  <style>
                    body {{ font-family:'Inter',sans-serif; background:#fafafa; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
                    .card {{ background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:48px; text-align:center; max-width:480px; box-shadow:0 4px 6px rgba(0,0,0,0.07); }}
                    .icon {{ font-size:64px; margin-bottom:24px; }}
                    h1 {{ font-size:28px; font-weight:700; color:#0f172a; margin-bottom:12px; }}
                    p {{ color:#64748b; margin-bottom:24px; line-height:1.6; }}
                    .btn {{ display:inline-block; padding:14px 28px; background:#4f46e5; color:#fff; border-radius:8px; font-weight:600; text-decoration:none; margin:8px; }}
                    .btn-outline {{ background:transparent; color:#4f46e5; border:1.5px solid #4f46e5; }}
                  </style>
                </head>
                <body>
                  <div class="card">
                    <div class="icon">✅</div>
                    <h1>Payment Successful!</h1>
                    <p>Thank you for purchasing <strong>{product['name']}</strong>.<br>Your download link has been sent to your email.</p>
                    <a href="/api/download/{product_id}?session={session_id}" class="btn">⬇️ Download Now</a>
                    <a href="/" class="btn btn-outline">Browse More Tools</a>
                  </div>
                </body>
                </html>
                """
    except Exception as e:
        pass

    return redirect('/')

@app.route('/api/download/<product_id>')
def download(product_id):
    """Deliver file after verified payment"""
    session_id = request.args.get('session')
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
            product = PRODUCTS.get(product_id)
            if product and os.path.exists(product['file']):
                return send_file(product['file'], as_attachment=True)
            else:
                return "File will be delivered to your email within 24 hours.", 200
    except Exception as e:
        pass
    return "Invalid download link.", 403

@app.route('/tip-thanks')
def tip_thanks():
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <title>Thank You — Hardin AI Marketplace</title>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
      <style>
        body { font-family:'Inter',sans-serif; background:#fafafa; display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }
        .card { background:#fff; border:1px solid #e2e8f0; border-radius:16px; padding:48px; text-align:center; max-width:480px; }
        h1 { font-size:28px; font-weight:700; color:#0f172a; margin-bottom:12px; }
        p { color:#64748b; margin-bottom:24px; }
        .btn { display:inline-block; padding:14px 28px; background:#4f46e5; color:#fff; border-radius:8px; font-weight:600; text-decoration:none; }
      </style>
    </head>
    <body>
      <div class="card">
        <div style="font-size:64px;margin-bottom:24px;">❤️</div>
        <h1>Thank You!</h1>
        <p>Your support means everything to us. It helps us keep the marketplace running and improving.</p>
        <a href="/" class="btn">Back to Marketplace</a>
      </div>
    </body>
    </html>
    """

@app.route('/cancel')
def cancel():
    return redirect('/')

@app.route('/api/submit', methods=['POST'])
def submit_tool():
    """Handle tool submission for review"""
    data = request.json or {}
    submission = {
        'submitted_at': datetime.now().isoformat(),
        'name': data.get('name'),
        'email': data.get('email'),
        'tool_name': data.get('tool_name'),
        'description': data.get('description'),
        'price': data.get('price'),
        'category': data.get('category'),
        'status': 'pending_review',
    }
    # Save to submissions file
    submissions = []
    try:
        with open('data/submissions.json') as f:
            submissions = json.load(f)
    except Exception:
        pass
    submissions.append(submission)
    os.makedirs('data', exist_ok=True)
    with open('data/submissions.json', 'w') as f:
        json.dump(submissions, f, indent=2)

    return jsonify({'success': True, 'message': 'Submission received! We will review within 48 hours.'})

@app.route('/api/admin/submissions')
def admin_submissions():
    """Admin view of pending submissions"""
    token = request.headers.get('X-Admin-Token')
    if token != os.getenv('ADMIN_TOKEN', 'hardinai-admin-2026'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        with open('data/submissions.json') as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])

@app.route('/api/admin/sales')
def admin_sales():
    """Admin view of all sales"""
    token = request.headers.get('X-Admin-Token')
    if token != os.getenv('ADMIN_TOKEN', 'hardinai-admin-2026'):
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        with open('data/sales.json') as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])

@app.route('/api/admin/approve', methods=['POST'])
def admin_approve():
    """Approve a submission"""
    token = request.headers.get('X-Admin-Token')
    if token != os.getenv('ADMIN_TOKEN', 'hardinai-admin-2026'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json or {}
    # Update submission status
    try:
        with open('data/submissions.json') as f:
            submissions = json.load(f)
        for s in submissions:
            if s.get('email') == data.get('email') and s.get('tool_name') == data.get('tool_name'):
                s['status'] = 'approved'
                s['approved_at'] = datetime.now().isoformat()
        with open('data/submissions.json', 'w') as f:
            json.dump(submissions, f, indent=2)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'success': True})

@app.route('/api/admin/reject', methods=['POST'])
def admin_reject():
    """Reject a submission"""
    token = request.headers.get('X-Admin-Token')
    if token != os.getenv('ADMIN_TOKEN', 'hardinai-admin-2026'):
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json or {}
    try:
        with open('data/submissions.json') as f:
            submissions = json.load(f)
        for s in submissions:
            if s.get('email') == data.get('email') and s.get('tool_name') == data.get('tool_name'):
                s['status'] = 'rejected'
                s['rejected_at'] = datetime.now().isoformat()
        with open('data/submissions.json', 'w') as f:
            json.dump(submissions, f, indent=2)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'success': True})

def _log_sale(session, product_id, product):
    """Log completed sale"""
    os.makedirs('data', exist_ok=True)
    sales = []
    try:
        with open('data/sales.json') as f:
            sales = json.load(f)
    except Exception:
        pass
    sales.append({
        'date': datetime.now().isoformat(),
        'product_id': product_id,
        'product_name': product['name'],
        'amount': product['price'] / 100,
        'session_id': session.id,
        'customer_email': session.get('customer_details', {}).get('email', 'unknown'),
    })
    with open('data/sales.json', 'w') as f:
        json.dump(sales, f, indent=2)


if __name__ == '__main__':
    port = int(os.getenv('MARKETPLACE_PORT', 5001))
    print(f"\n✅ Marketplace backend running on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)

