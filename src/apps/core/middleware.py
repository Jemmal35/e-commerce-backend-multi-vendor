import json
from apps.core.models import ActivityLog

SENSITIVE_KEYS = {'password', 'token', 'secret', 'credit_card', 'card_number'}

def filter_sensitive_data(data):
    if not isinstance(data, dict):
        return {}
    filtered = {}
    for key, value in data.items():
        if key.lower() in SENSITIVE_KEYS:
            filtered[key] = "********"
        elif isinstance(value, dict):
            filtered[key] = filter_sensitive_data(value)
        else:
            filtered[key] = value
    return filtered

class ActivityLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Determine if we should log this request
        should_log = (
            request.method in ['POST', 'PUT', 'PATCH', 'DELETE'] 
            and not ('/api/v1/auth/' in request.path)
        )

        # 2. Extract IP address beforehand
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip_address:
            ip_address = ip_address.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # 3. Safely read request.body BEFORE get_response() consumes the stream
        payload = {}
        if should_log and request.content_type == 'application/json':
            try:
                if request.body:
                    payload = json.loads(request.body)
                    payload = filter_sensitive_data(payload)
            except (json.JSONDecodeError, Exception):
                payload = {}

        # Capture actor and request details early
        actor = request.user if request.user.is_authenticated else None
        path = request.path
        method = request.method

        # 4. NOW let the view process the request
        response = self.get_response(request)

        # 5. Create the activity log using the status code from the response
        if should_log:
            ActivityLog.objects.create(
                actor=actor,
                method=method,
                path=path,
                status_code=response.status_code,
                ip_address=ip_address,
                request_payload=payload
            )

        return response