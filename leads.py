from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        location = params.get("location", ["Crossville, TN"])[0].strip()[:100]
        service = params.get("service", ["property management"])[0].strip()[:100]

        if not location or not service:
            return self.send_json({"success": False, "error": "Location and business type are required."}, 400)

        api_key = os.environ.get("YELP_API_KEY")
        if not api_key:
            return self.send_json({"success": False, "error": "YELP_API_KEY is not configured in Vercel."}, 500)

        query = urllib.parse.urlencode({"location": location, "term": service, "limit": 20, "sort_by": "distance"})
        request = urllib.request.Request(
            f"https://api.yelp.com/v3/businesses/search?{query}",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        )

        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))

            results = []
            for business in payload.get("businesses", []):
                results.append({
                    "name": business.get("name", "Unknown business"),
                    "address": ", ".join(business.get("location", {}).get("display_address", [])),
                    "phone": business.get("display_phone") or business.get("phone"),
                    "rating": business.get("rating"),
                    "review_count": business.get("review_count", 0),
                    "url": business.get("url"),
                })

            return self.send_json({"success": True, "location": location, "service": service, "results": results})
        except urllib.error.HTTPError as error:
            message = "The business search provider rejected the request. Check the Yelp API key."
            if error.code == 429:
                message = "The Yelp search limit has been reached. Please try again later."
            return self.send_json({"success": False, "error": message}, error.code)
        except Exception:
            return self.send_json({"success": False, "error": "The business search is temporarily unavailable."}, 502)

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
      
