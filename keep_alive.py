from flask import Flask, jsonify
from threading import Thread
from datetime import datetime

app = Flask('')

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Bot Status</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
            }
            .container {
                text-align: center;
                background: rgba(255,255,255,0.1);
                padding: 40px;
                border-radius: 20px;
                backdrop-filter: blur(10px);
            }
            h1 { font-size: 3em; margin: 0; }
            .status { font-size: 1.5em; margin: 20px 0; }
            .emoji { font-size: 5em; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">🤖</div>
            <h1>AI Bot is Running!</h1>
            <div class="status">✅ Status: <strong>ACTIVE</strong></div>
            <p>Powered by Google Gemini AI</p>
            <p>100% Free Forever 🆓</p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "bot": "running",
        "service": "Google Gemini AI",
        "cost": "FREE",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/ping')
def ping():
    return "pong", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """Запускает Flask сервер в отдельном потоке"""
    server_thread = Thread(target=run)
    server_thread.daemon = True
    server_thread.start()
    print("✅ Keep-alive сервер запущен на порту 8080")