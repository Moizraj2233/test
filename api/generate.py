import json
import re
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def product_terms(script):
    found = []
    for pattern in (
        r"\b(?:[A-Z][a-zA-Z0-9-]*\s+){1,4}(?:Pro|Plus|Max|Mini|Air|Ultra|4K|Mk\s?\d+)\b",
        r"\b[A-Z][a-zA-Z0-9-]*(?:\s+[A-Z0-9][a-zA-Z0-9-]*){1,3}\b",
    ):
        for match in re.finditer(pattern, script):
            term = match.group(0).strip()
            if term.lower() not in {x.lower() for x in found} and term.lower() not in {
                "in this", "thank you", "let me", "make sure", "amazon associates",
                "this video", "the product", "for example", "on amazon",
            }:
                found.append(term)
    return found[:8]


def search_items(query, marketplace, tag, client_id, client_secret):
    token_req = Request(
        "https://api.amazon.com/auth/o2/token",
        data=json.dumps({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "creatorsapi::default",
        }).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urlopen(token_req, timeout=25) as response:
        token = json.load(response)["access_token"]
    payload = {
        "keywords": query, "partnerTag": tag, "marketplace": marketplace,
        "searchIndex": "All", "itemCount": 5, "resources": ["itemInfo.title"],
    }
    request = Request(
        "https://creatorsapi.amazon/catalog/v1/searchItems",
        data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json", "x-marketplace": marketplace},
        method="POST",
    )
    with urlopen(request, timeout=25) as response:
        return json.load(response).get("searchResult", {}).get("items", [])


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            terms = product_terms(data["script"])
            if not terms:
                raise ValueError("Could not spot a product name. Include brand or model names clearly in the script.")
            products = []
            for term in terms:
                items = search_items(term, data["marketplace"], data["tag"], data["clientId"], data["clientSecret"])
                products.append({"mention": term, "matches": [
                    {"title": item.get("itemInfo", {}).get("title", {}).get("displayValue", "Amazon item"),
                     "url": item.get("detailPageURL", "")}
                    for item in items if item.get("detailPageURL")
                ][:3]})
            self._respond(200, {"products": products})
        except HTTPError as error:
            if error.code == 401:
                message = "Amazon credentials were not accepted. Check your API Client ID and Secret."
            else:
                message = f"Amazon API returned HTTP {error.code}. Check your marketplace, tracking tag, and API access."
            self._respond(400, {"error": message})
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self._respond(400, {"error": str(error) or "Check all fields and try again."})
        except (URLError, TimeoutError):
            self._respond(502, {"error": "Could not connect to Amazon. Try again shortly."})
        except Exception:
            self._respond(500, {"error": "The search failed. Check your fields and try again."})

    def do_GET(self):
        self._respond(405, {"error": "Use POST."})

    def _respond(self, status, body):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

