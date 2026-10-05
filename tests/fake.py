"""A requests.Session stand-in for the Supertext API that "translates" by prefixing text."""

import json
import re

import requests


class FakeSession(requests.Session):
    def __init__(self, *, statuses=("done",), rate_limited=0, fail_status=None, translate=None):
        super().__init__()
        self.calls = []
        self.files = {}
        self.statuses = list(statuses)
        self.rate_limited = rate_limited
        self.fail_status = fail_status
        self.translate = translate or (lambda target, html: re.sub(r">([^<>]+)<", lambda m: f">[{target}] {m.group(1)}<" if m.group(1).strip() else m.group(0), html))

    def request(self, method, url, headers=None, data=None, files=None, **kwargs):
        self.calls.append({"method": method, "url": url, "headers": headers or {}, "data": data, "files": files})
        if (headers or {}).get("Authorization") != "Supertext-Auth-Key test-key":
            return response(401, "bad key")
        if self.fail_status:
            return response(self.fail_status, "nope")
        if self.rate_limited:
            self.rate_limited -= 1
            return response(429, '{"error_code":"RATE_LIMIT_EXCEEDED"}')
        path = url.split("/v1/", 1)[1]
        if method == "POST" and path == "translate/ai/file":
            name, content, content_type = files["file"]
            file_id = f"f{len(self.files) + 1}"
            self.files[file_id] = {"html": content.decode(), "target": data["target_lang"], "type": content_type, "polls": 0}
            return response(200, json.dumps({"file_id": file_id}))
        if path == "features":
            return response(200, "{}")
        match = re.match(r"translate/ai/file/(\w+)(/status|/translation)?$", path)
        file = self.files.get(match.group(1)) if match else None
        if not file:
            return response(404, "not found")
        if method == "DELETE":
            return response(200, "{}")
        if match.group(2) == "/status":
            status = self.statuses[min(file["polls"], len(self.statuses) - 1)]
            file["polls"] += 1
            return response(200, json.dumps({"status": status}))
        return response(200, self.translate(file["target"], file["html"]))


def response(status, text):
    r = requests.Response()
    r.status_code = status
    r._content = text.encode()
    r.encoding = "utf-8"
    return r
