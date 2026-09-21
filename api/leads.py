from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.error
import urllib.parse
import urllib.request


GOOGLE_URL = "https://places.googleapis.com/v1/places:searchText"


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

        api_key = os.environ.get("GOOGLE_PLACES_API_KEY")

        if not api_key:
            return self.send_json(
                {
                    "success": False,
                    "error": (
                        "GOOGLE_PLACES_API_KEY is not configured "
                        "in Vercel."
                    ),
                },
                500,
            )

        request_body = json.dumps(
            {
                "textQuery": f"{service} near {location}",
                "pageSize": 20,
                "languageCode": "en",
                "regionCode": "US",
            }
        ).encode("utf-8")

        field_mask = ",".join(
            [
                "places.id",
                "places.displayName",
                "places.formattedAddress",
                "places.nationalPhoneNumber",
                "places.rating",
                "places.userRatingCount",
                "places.websiteUri",
                
                "places.businessStatus",
            ]
        )

        request = urllib.request.Request(
            GOOGLE_URL,
            data=request_body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": field_mask,
            },
        )

        try:
            with urllib.request.urlopen(
                request, timeout=20
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

            results = []

            for place in payload.get("places", []):
                if place.get("businessStatus") == "CLOSED_PERMANENTLY":
                    continue

                display_name = place.get("displayName") or {}
                name = display_name.get("text", "Unknown business")

                                results.append(
                    {
                        "name": name,
                        "address": place.get(
                            "formattedAddress",
                            "Address unavailable",
                        ),
                        "phone": place.get(
                            "nationalPhoneNumber",
                            "",
                        ),
                        "rating": place.get("rating"),
                        "review_count": place.get(
                            "userRatingCount",
                            0,
                        ),
                        "url": (
                            place.get("websiteUri")
                            or (
                                "https://www.google.com/maps/place/?q=place_id:"
                                + place.get("id", "")
                            )
                        ),
                    }
                                )
            return self.send_json(
                {
                    "success": True,
                    "location": location,
                    "service": service,
                    "provider": "Google Places",
                    "results": results,
                }
            )

        except urllib.error.HTTPError as error:
            if error.code in (401, 403):
                message = (
                    "Google rejected the API key. Make sure "
                    "Places API (New) and billing are enabled."
                )
            elif error.code == 429:
                message = (
                    "The Google Places search limit was reached. "
                    "Please try again later."
                )
            else:
                message = (
                    "Google Places could not complete the search."
                )

            return self.send_json(
                {"success": False, "error": message},
                error.code,
            )

        except Exception:
            return self.send_json(
                {
                    "success": False,
                    "error": (
                        "The business search is temporarily "
                        "unavailable."
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
