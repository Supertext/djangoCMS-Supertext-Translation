"""The public ping endpoint of the Commando Center (no login, no session, GET only)."""

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from . import reporting


@csrf_exempt
@require_GET
def ping(request):
    """``GET …/ping?challenge=<c>``: the SDK's answer (200 echoing the challenge, 400, or 404 with reports off)."""
    answer = reporting.ping(request.GET.get("challenge"))
    response = HttpResponse(answer.body, status=answer.status, content_type=answer.headers.get("Content-Type", "application/json"))
    for name, value in answer.headers.items():
        response[name] = value
    return response
