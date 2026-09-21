from http.server import BaseHTTPRequestHandler
import json
import urllib.error
import urllib.parse
import urllib.request


USER_AGENT = "JA-Local-Lead-Hunter/1.0"


def fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        location = params.get(
            "location", ["Crossville, TN"]
        )[0].strip()[:100]

        service = params.get(
            "service", ["property management"]
        )[0].strip()[:100]

        if not location or not service:
            return self.send_json(
                {
                    "success": False,
                    "error": "Location and business type are required.",
                },
                400,
            )

        query = urllib.parse.urlencode(
            {
                "q": f"{service}, {location}",
                "format": "jsonv2",
                "addressdetails": 1,
                "extratags": 1,
                "namedetails": 1,
                "countrycodes": "us",
                "limit": 20,
            }
        )

        try:
            places = fetch_json(
                "https://nominatim.openstreetmap.org/search?"
                + query
            )

            results = []
            seen = set()

            for place in places:
                extra = place.get("extratags") or {}
                names = place.get("namedetails") or {}

                name = (
                    names.get("name")
                    or str(place.get("display_name", "")).split(",")[0]
                )

                if not name or name.casefold() in seen:
                    continue

                seen.add(name.casefold())

                osm_type = place.get("osm_type", "node")
                osm_id = place.get("osm_id")

                website = (
                    extra.get("contact:website")
                    or extra.get("website")
                    or f"https://www.openstreetmap.org/"
                    f"{osm_type}/{osm_id}"
                )

                phone = (
                    extra.get("contact:phone")
                    or extra.get("phone")
                    or ""
                )

                results.append(
                    {
                        "name": name,
                        "address": place.get(
                            "display_name",
                            "Address unavailable",
                        ),
                        "phone": phone,
                        "rating": None,
                        "review_count": 0,
                        "url": website,
                    }
                )

            return self.send_json(
                {
                    "success": True,
                    "location": location,
                    "service": service,
                    "provider": "OpenStreetMap",
                    "results": results,
                }
            )

        except urllib.error.HTTPError as error:
            if error.code == 429:
                message = (
                    "The free map search is busy. "
                    "Wait a minute and try again."
                )
            else:
                message = (
                    "The local business search is "
                    "temporarily unavailable."
                )

            return self.send_json(
                {"success": False, "error": message},
                502,
            )

        except Exception:
            return self.send_json(
                {
                    "success": False,
                    "error": (
                        "The local business search is "
                        "temporarily unavailable."
                    ),
                },
                502,
            )

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8",
        )
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
