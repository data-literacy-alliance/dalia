"""
SPARQL proxy view: forwards read-only SPARQL queries to Fuseki.

Replaces the Next.js API route /sparql-api/route.ts.
Security: rejects write keywords, blocks SERVICE clause (SSRF), caps LIMIT at 1000.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import urljoin

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

_WRITE_KEYWORDS = re.compile(
    r'\b(INSERT|DELETE|DROP|CLEAR|CREATE|LOAD|ADD|MOVE|COPY)\b',
    re.IGNORECASE,
)
_SERVICE_CLAUSE = re.compile(r'\bSERVICE\b', re.IGNORECASE)
_LIMIT_CLAUSE = re.compile(r'\bLIMIT\s+(\d+)\b', re.IGNORECASE)
_MAX_LIMIT = 1000


def _enforce_limit(query: str) -> str:
    match = _LIMIT_CLAUSE.search(query)
    if match:
        if int(match.group(1)) > _MAX_LIMIT:
            query = _LIMIT_CLAUSE.sub(f'LIMIT {_MAX_LIMIT}', query)
    else:
        query = query.rstrip() + f'\nLIMIT {_MAX_LIMIT}'
    return query


def _cors_headers(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response


@method_decorator(csrf_exempt, name='dispatch')
class SPARQLProxyView(View):

    def options(self, request, *args, **kwargs):
        return _cors_headers(JsonResponse({}))

    def get(self, request, *args, **kwargs):
        return self._proxy(request.GET.get('query', ''))

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            query = data.get('query', '')
        except (json.JSONDecodeError, UnicodeDecodeError):
            query = request.POST.get('query', '')
        return self._proxy(query)

    def _proxy(self, query: str):
        if not query or not query.strip():
            return _cors_headers(JsonResponse({'error': 'No query provided'}, status=400))

        if _WRITE_KEYWORDS.search(query):
            return _cors_headers(JsonResponse({'error': 'Write operations are not allowed'}, status=403))

        if _SERVICE_CLAUSE.search(query):
            return _cors_headers(JsonResponse({'error': 'SERVICE clause is not allowed'}, status=403))

        query = _enforce_limit(query)

        base_url = getattr(settings, 'DALIA_TRIPLESTORE_BASE_URL', 'http://daliaproject_prod-fuseki_1:3030/')
        fuseki_url = urljoin(base_url, 'dalia/query')

        post_data = urllib.parse.urlencode({'query': query}).encode('utf-8')
        req = urllib.request.Request(
            fuseki_url,
            data=post_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/sparql-results+json',
            },
            method='POST',
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read()
                content_type = resp.headers.get('Content-Type', 'application/sparql-results+json')
                return _cors_headers(HttpResponse(body, content_type=content_type, status=resp.status))
        except urllib.error.HTTPError as e:
            return _cors_headers(JsonResponse({'error': 'Query failed', 'details': str(e.reason)}, status=e.code))
        except urllib.error.URLError as e:
            return _cors_headers(JsonResponse({'error': 'Triplestore unavailable', 'details': str(e.reason)}, status=503))
        except TimeoutError:
            return _cors_headers(JsonResponse({'error': 'Query timed out'}, status=504))
