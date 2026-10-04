from http.server import BaseHTTPRequestHandler
import json
import os
import re
import uuid
import urllib.request
import urllib.error

SERVICES = {"Tree removal", "Tree pruning", "Storm cleanup", "Lawn and grounds care", "Other"}
TIMINGS = {"As soon as possible", "Within two weeks", "Within a month", "Just planning"}

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Invalid request.")
    if data.get("website"):
        raise ValueError("Unable to accept this request.")
    limits = {"name":100, "phone":30, "email":254, "address":250, "city":100, "zip":10, "service":40, "timing":40, "description":2000}
    row = {}
    for field, limit in limits.items():
        value = data.get(field, "")
        if not isinstance(value, str) or len(value) > limit:
            raise ValueError("Please check the " + field + " field.")
        row[field] = value.strip()
        if field != "email" and not row[field]:
            raise ValueError("Please complete the " + field + " field.")
    if len(re.sub(r"\D", "", row["phone"])) not in range(10, 16):
        raise ValueError("Enter a valid phone number including area code.")
    if not re.fullmatch(r"\d{5}(-\d{4})?", row["zip"]):
        raise ValueError("Enter a valid ZIP code.")
    if row["email"] and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", row["email"]):
        raise ValueError("Enter a valid email address.")
    if row["service"] not in SERVICES or row["timing"] not in TIMINGS:
        raise ValueError("Choose a valid service and timing.")
    if data.get("consent") is not True:
        raise ValueError("Contact permission is required.")
    try:
        row["id"] = str(uuid.UUID(data.get("request_id", "")))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid request reference. Reload this page and try again.")
    row["consent"] = True
    row["source"] = "customer_form"
    return row

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            return self.send_json({"error":"Send a JSON request."}, 415)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 16000:
                return self.send_json({"error":"Request is too large or empty."}, 413)
            row = validate(json.loads(self.rfile.read(length)))
        except (ValueError, UnicodeDecodeError) as error:
            return self.send_json({"error":str(error)}, 400)
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url.startswith("https://") or not key:
            return self.send_json({"error":"The request form is not connected yet. Please try again later."}, 503)
        request = urllib.request.Request(
            url + "/rest/v1/customer_requests?on_conflict=id", data=json.dumps(row).encode(), method="POST",
            headers={"apikey":key, "Authorization":"Bearer " + key, "Content-Type":"application/json", "Prefer":"resolution=ignore-duplicates,return=minimal"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                response.read()
        except (urllib.error.URLError, TimeoutError):
            return self.send_json({"error":"We could not confirm your request. Please try again; your details are still in the form."}, 502)
        return self.send_json({"success":True, "request_id":row["id"]}, 201)

    def send_json(self, payload, status):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
