import requests
from urllib.parse import urljoin, urlparse
from flask import Flask, request, Response

app = Flask(__name__)

ALLOWED_TARGETS = {
    "213.142.135.46:9999",
    "1.2.3.4:8000"
}

@app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
def proxy(path):
    target_param = request.args.get("target")
    if not target_param:
        return Response("Missing ?target= URL parameter", status=400)

    parsed = urlparse(target_param)
    if not parsed.scheme.startswith("http") or not parsed.netloc:
        return Response("Invalid target URL", status=400)

    if parsed.netloc not in ALLOWED_TARGETS:
        return Response("Target not allowed", status=403)

    proxy_target = f"{parsed.scheme}://{parsed.netloc}"
    forward_url = urljoin(proxy_target + '/', path)

    filtered_query = '&'.join(f"{k}={v}" for k, v in request.args.items() if k != "target")
    if filtered_query:
        forward_url += '?' + filtered_query

    headers = {key: value for key, value in request.headers if key.lower() != "host"}

    try:
        resp = requests.request(
            method=request.method,
            url=forward_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            stream=True
        )
    except requests.RequestException as e:
        return Response(f"Upstream error: {str(e)}", status=502)

    response = Response(resp.content, status=resp.status_code)
    excluded_headers = {"content-encoding", "transfer-encoding", "content-length", "connection"}
    for key, value in resp.headers.items():
        if key.lower() not in excluded_headers:
            response.headers[key] = value

    return response

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
  
