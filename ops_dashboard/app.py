import os
import requests
import msal
from flask import Flask, render_template, request, session, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- CONFIGURATION ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_PATH = "/getAToken"
SCOPE = ["User.Read"]

# Connect to Local Worker API (Internal traffic via HTTP is fine locally)
AZURE_WORKER_URL = "http://localhost:5000/api/status"
AZURE_API_KEY = os.getenv("AZURE_API_KEY")

def _build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=AUTHORITY,
        client_credential=CLIENT_SECRET, token_cache=cache)

@app.route("/")
def index():
    if not session.get("user"):
        return redirect(url_for("login"))
    
    # 1. Fetch Worker Status
    worker_data = {"status": "offline", "queue_depth": 0, "active_workers": 0}
    try:
        response = requests.get(
            AZURE_WORKER_URL, 
            headers={"X-API-Key": AZURE_API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            worker_data = response.json()
    except Exception as e:
        print(f"Error connecting to worker: {e}")

    # 2. Mock Logs
    logs = ["System ready.", "Waiting for logs..."]

    return render_template(
        "dashboard.html", 
        user=session["user"], 
        worker=worker_data, 
        logs=logs
    )

@app.route("/login")
def login():
    session["state"] = os.urandom(16).hex()
    auth_url = _build_msal_app().get_authorization_request_url(
        SCOPE,
        state=session["state"],
        redirect_uri=url_for("authorized", _external=True)
    )
    return render_template("login.html", auth_url=auth_url)

@app.route(REDIRECT_PATH)
def authorized():
    if request.args.get('state') != session.get("state"):
        return redirect(url_for("index"))
    if "error" in request.args:
        return render_template("login.html", error=request.args.get("error_description"))

    if request.args.get('code'):
        cache = _build_msal_app()
        result = cache.acquire_token_by_authorization_code(
            request.args['code'],
            scopes=SCOPE,
            redirect_uri=url_for("authorized", _external=True)
        )
        if "error" in result:
            return render_template("login.html", error=result.get("error_description"))
        
        session["user"] = result.get("id_token_claims")
        return redirect(url_for("index"))
        
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(f"https://login.microsoftonline.com/common/oauth2/v2.0/logout?post_logout_redirect_uri={url_for('index', _external=True)}")

if __name__ == "__main__":
    # ENABLED HTTPS HERE
    app.run(host='0.0.0.0', port=8000, ssl_context='adhoc')
