"""A requests.Session stand-in for the Supertext API that "translates" by prefixing text."""

import json
import re
from email.parser import BytesParser
from email.policy import HTTP

import requests

from djangocms_supertext._vendor.supertext.v1 import Languages

#: Exactly the codes the live API accepts as targets (the SDK's list, from GET features).
TARGETS = {language.code: language for language in Languages.TARGETS}
#: Where the tests send version reports (tests/settings.py sets SUPERTEXT_REPORT_URL to it).
REPORT_URL = "https://center.test/api/v1/report"


def parse_multipart(content_type, body):
    """multipart/form-data body -> (fields, files) like requests' data= and files= arguments."""
    message = BytesParser(policy=HTTP).parsebytes(f"Content-Type: {content_type}\r\n\r\n".encode() + body)
    fields, files = {}, {}
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        payload = part.get_payload(decode=True)
        if part.get_filename():
            files[name] = (part.get_filename(), payload, part.get("content-type"))
        else:
            fields[name] = payload.decode()
    return fields, files


class FakeSession(requests.Session):
    def __init__(self, *, statuses=("done",), rate_limited=0, fail_status=None, translate=None):
        super().__init__()
        self.calls = []
        self.reports = []
        self.feature_status = 200
        self.files = {}
        self.statuses = list(statuses)
        self.rate_limited = rate_limited
        self.fail_status = fail_status
        self.translate = translate or (lambda target, html: re.sub(r">([^<>]+)<", lambda m: f">[{target}] {m.group(1)}<" if m.group(1).strip() else m.group(0), html))

    def request(self, method, url, headers=None, data=None, files=None, **kwargs):
        if url == REPORT_URL:  # the Commando Center
            self.reports.append(json.loads(data))
            return response(202, '{"ok":true}')
        if isinstance(data, bytes):  # the SDK sends the multipart body itself
            data, files = parse_multipart((headers or {}).get("Content-Type", ""), data)
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
            target = TARGETS.get(data.get("target_lang", ""))
            if target is None:
                # Like the live API: only its exact codes ("de" or "es-ES" are not valid pairs).
                return response(404, json.dumps({"error_code": "INVALID_LANGUAGE_PAIR", "source_lang": data.get("source_lang"), "target_lang": data.get("target_lang")}))
            if data.get("politeness") and not target.politeness:
                return response(400, json.dumps({"error_code": "FEATURE_ERROR", "source_lang": data.get("source_lang"), "target_lang": target.code}))
            name, content, content_type = files["file"]
            file_id = f"f{len(self.files) + 1}"
            self.files[file_id] = {"html": content.decode(), "target": data["target_lang"], "type": content_type, "polls": 0}
            return response(200, json.dumps({"file_id": file_id}))
        if path == "features":
            return response(self.feature_status, "{}")
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
