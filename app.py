# app.py
"""
Single-file lightweight Flask app that serves both frontend and backend on port 5090.
Features:
 - Frontend: simple single-page app served at "/"
 - API: /api/items, /api/version, /api/health, /api/metrics
 - Auth: /api/auth/login -> returns JWT token (simple demo)
 - Protected: /api/secure (requires Authorization: Bearer <token>)
 - In-memory datastore (list) for demo CRUD
 - Versioning available via environment VERSION (default from file)
"""

from flask import Flask, jsonify, request, send_file, make_response, render_template_string
import os
import time
import uuid
import jwt
from functools import wraps
from datetime import datetime, timedelta

# Configuration
PORT = int(os.environ.get("PORT", 5090))
APP_NAME = os.environ.get("APP_NAME", "usman-apis-dashboard")
DOCKER_USER = os.environ.get("DOCKER_USER", "usmanfarooq317")   # from Jenkins env
IMAGE_NAME = os.environ.get("IMAGE_NAME", APP_NAME)
VERSION = os.environ.get("VERSION", "v1")
JWT_SECRET = os.environ.get("JWT_SECRET", "supersecret_demo_key")  # change in production
JWT_ALGO = "HS256"
TOKEN_EXP_MINUTES = 60

app = Flask(__name__)

# In-memory datastore
_items = {}
_start_time = time.time()

# Helper: create sample items
def _create_sample_items():
    for i in range(1, 4):
        id = str(uuid.uuid4())
        _items[id] = {
            "id": id,
            "name": f"Sample Item {i}",
            "description": f"A sample item number {i}",
            "created_at": datetime.utcnow().isoformat() + "Z"
        }

_create_sample_items()

# Auth helpers
def generate_token(username):
    payload = {
        "sub": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXP_MINUTES * 60,
        "iss": APP_NAME,
        "ver": VERSION
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    # PyJWT >= 2 returns str; ensure string
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth.split(" ", 1)[1]
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO], options={"verify_aud": False})
            request.user = decoded.get("sub")
        except Exception as e:
            return jsonify({"error": "Invalid or expired token", "detail": str(e)}), 401
        return f(*args, **kwargs)
    return decorated

# ----------------------
# Frontend (single-page)
# ----------------------
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{{app_name}} — Demo (port {{port}})</title>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <style>
    body { font-family: Inter, Arial, sans-serif; padding: 18px; max-width: 900px; margin: auto; }
    header { display:flex; gap:12px; align-items:center; margin-bottom:18px;}
    input, button, textarea { padding:8px; font-size:14px; }
    .item { border:1px solid #ddd; padding:10px; border-radius:8px; margin-bottom:8px;}
    .row { display:flex; gap:8px; align-items:center; }
  </style>
</head>
<body>
  <header>
    <h1>{{app_name}}</h1>
    <small>version: <span id="version">{{version}}</span></small>
  </header>

  <section>
    <h2>Auth</h2>
    <div class="row">
      <input id="username" placeholder="username (demo)" value="demo_user"/>
      <input id="password" placeholder="password (demo)" value="demo_pass"/>
      <button onclick="login()">Login (get JWT)</button>
      <button onclick="logout()">Logout</button>
    </div>
    <div>Token: <code id="tokenPreview" style="word-break:break-all"></code></div>
  </section>

  <section>
    <h2>Items (CRUD)</h2>
    <div>
      <input id="itemName" placeholder="name"/>
      <input id="itemDesc" placeholder="description"/>
      <button onclick="createItem()">Create</button>
    </div>
    <div id="items"></div>
  </section>

  <section>
    <h2>App Info</h2>
    <button onclick="loadInfo()">Reload Info</button>
    <pre id="info"></pre>
  </section>

<script>
const apiRoot = "/api";

function setToken(t) {
  localStorage.setItem("jwt_token", t||"");
  document.getElementById("tokenPreview").innerText = t || "";
}
function getToken() {
  return localStorage.getItem("jwt_token") || "";
}

async function login(){
  const u = document.getElementById("username").value;
  const p = document.getElementById("password").value;
  const res = await fetch(apiRoot + "/auth/login", {
    method: "POST", headers: {'Content-Type':'application/json'}, body: JSON.stringify({username:u,password:p})
  });
  const j = await res.json();
  if(res.ok && j.token){ setToken(j.token); alert("Logged in"); loadItems(); }
  else alert("Login failed: " + JSON.stringify(j));
}

function logout(){ setToken(""); alert("Logged out"); loadItems(); }

async function authFetch(url, opts={}){
  opts.headers = opts.headers || {};
  const t = getToken();
  if(t) opts.headers['Authorization'] = 'Bearer ' + t;
  if(!opts.method) opts.method = 'GET';
  const r = await fetch(url, opts);
  return r;
}

async function loadItems(){
  const r = await fetch(apiRoot + "/items");
  const list = await r.json();
  const el = document.getElementById("items");
  el.innerHTML = "";
  list.forEach(it=>{
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `
      <b>${it.name}</b> <small>${it.id}</small>
      <p>${it.description}</p>
      <div class="row">
        <button onclick='editItem("${it.id}")'>Edit</button>
        <button onclick='deleteItem("${it.id}")'>Delete</button>
        <button onclick='callSecure("${it.id}")'>Call Secure</button>
      </div>
    `;
    el.appendChild(div);
  });
}

async function createItem(){
  const name = document.getElementById("itemName").value;
  const desc = document.getElementById("itemDesc").value;
  const r = await fetch(apiRoot + "/items", {
    method: "POST", headers: {'Content-Type':'application/json'}, body: JSON.stringify({name,description:desc})
  });
  if(r.ok) { loadItems(); document.getElementById("itemName").value=""; document.getElementById("itemDesc").value=""; }
  else alert("Create failed: " + await r.text());
}

async function editItem(id){
  const newName = prompt("New name?");
  if(!newName) return;
  const r = await fetch(apiRoot + "/items/" + id, {
    method: "PUT", headers: {'Content-Type':'application/json'}, body: JSON.stringify({name:newName})
  });
  if(r.ok) loadItems(); else alert("Edit failed");
}

async function deleteItem(id){
  if(!confirm("Delete?")) return;
  const r = await fetch(apiRoot + "/items/" + id, { method: "DELETE" });
  if(r.ok) loadItems();
  else alert("Delete failed");
}

async function loadInfo(){
  const p = await fetch(apiRoot + "/version"); const v = await p.json();
  const h = await fetch(apiRoot + "/health"); const healthy = await h.json();
  const m = await fetch(apiRoot + "/metrics"); const metrics = await m.json();
  document.getElementById("info").innerText = JSON.stringify({version:v,health:healthy,metrics:metrics}, null, 2);
  document.getElementById("version").innerText = v.version;
}

async function callSecure(id){
  const token = getToken();
  if(!token){ alert("You must login first"); return; }
  const r = await fetch(apiRoot + "/secure", { headers: {'Authorization':'Bearer ' + token} });
  alert(await r.text());
}

window.onload = function(){ loadItems(); loadInfo(); setToken(getToken()); }
</script>
</body>
</html>
"""

# ----------------------
# Routes - Frontend
# ----------------------
@app.route("/", methods=["GET"])
def index():
    return render_template_string(INDEX_HTML, app_name=APP_NAME, port=PORT, version=VERSION)

# ----------------------
# API: basic info
# ----------------------
@app.route("/api/version", methods=["GET"])
def api_version():
    return jsonify({
        "app": APP_NAME,
        "version": VERSION,
        "image": f"{DOCKER_USER}/{IMAGE_NAME}"
    })

@app.route("/api/health", methods=["GET"])
def api_health():
    uptime = time.time() - _start_time
    return jsonify({
        "status": "ok",
        "uptime_seconds": int(uptime),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    return jsonify({
        "items_count": len(_items),
        "memory_dummy": 0,
        "requests": 0
    })

# ----------------------
# Auth endpoints
# ----------------------
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    payload = request.json or {}
    username = payload.get("username")
    password = payload.get("password")
    # In real world verify password; here hardcoded for demo
    if username and password:
        # simple demo: accept anything where password contains "demo" OR username==demo_user
        if "demo" in password or username == "demo_user":
            token = generate_token(username)
            return jsonify({"token": token, "expires_in_minutes": TOKEN_EXP_MINUTES})
    return jsonify({"error": "invalid credentials"}), 401

# ----------------------
# CRUD items
# ----------------------
@app.route("/api/items", methods=["GET"])
def list_items():
    return jsonify(list(_items.values()))

@app.route("/api/items", methods=["POST"])
def create_item():
    body = request.json or {}
    name = body.get("name")
    desc = body.get("description", "")
    if not name:
        return jsonify({"error": "name required"}), 400
    id = str(uuid.uuid4())
    obj = {"id": id, "name": name, "description": desc, "created_at": datetime.utcnow().isoformat() + "Z"}
    _items[id] = obj
    return jsonify(obj), 201

@app.route("/api/items/<id>", methods=["GET"])
def get_item(id):
    if id not in _items:
        return jsonify({"error": "not found"}), 404
    return jsonify(_items[id])

@app.route("/api/items/<id>", methods=["PUT"])
def update_item(id):
    if id not in _items:
        return jsonify({"error": "not found"}), 404
    body = request.json or {}
    name = body.get("name")
    if name:
        _items[id]["name"] = name
    if "description" in body:
        _items[id]["description"] = body["description"]
    _items[id]["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return jsonify(_items[id])

@app.route("/api/items/<id>", methods=["DELETE"])
def delete_item(id):
    if id not in _items:
        return jsonify({"error": "not found"}), 404
    obj = _items.pop(id)
    return jsonify({"deleted": id})

# ----------------------
# Protected endpoint
# ----------------------
@app.route("/api/secure", methods=["GET"])
@token_required
def api_secure():
    user = getattr(request, "user", "unknown")
    return jsonify({"message": f"Hello {user}, this is a protected endpoint.", "issued_at": datetime.utcnow().isoformat() + "Z"})

# ----------------------
# Simulated operational endpoints
# ----------------------
@app.route("/api/simulate-task", methods=["POST"])
def simulate_task():
    """
    Simulate a synchronous task (for demo). Accepts JSON {"type":"heavy"|"light"}.
    """
    body = request.json or {}
    ttype = body.get("type", "light")
    start = time.time()
    # simulate work
    if ttype == "heavy":
        time.sleep(2)   # keep it short for demo
    else:
        time.sleep(0.2)
    elapsed = time.time() - start
    return jsonify({"type": ttype, "elapsed_seconds": round(elapsed, 3)})

# ----------------------
# Utility: graceful shutdown hint (not called automatically)
# ----------------------
@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    # This is a safe demo: do not expose publicly in production.
    if request.remote_addr not in ("127.0.0.1", "::1", "localhost"):
        return jsonify({"error":"shutdown allowed only from localhost"}), 403
    func = request.environ.get("werkzeug.server.shutdown")
    if func:
        func()
        return jsonify({"status": "shutting down"})
    return jsonify({"error": "not running with the Werkzeug Server"}), 500

# ----------------------
# Run
# ----------------------
if __name__ == "__main__":
    # Use built-in server for local dev. For production inside Docker use gunicorn command:
    # gunicorn -w 4 -b 0.0.0.0:5090 app:app
    print(f"Starting {APP_NAME} on port {PORT}, version {VERSION}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
