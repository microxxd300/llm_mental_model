from rest_framework.renderers import JSONRenderer


class EnvelopeJSONRenderer(JSONRenderer):
    """Wrap every response body in {data, error, message}"""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        status_code = getattr(response, "status_code", 200)

        if status_code >= 400:
            envelope = {"data": None, "error": data, "message": "Request failed"}
        else:
            envelope = {"data": data, "error": None, "message": "OK"}

        return super().render(envelope, accepted_media_type, renderer_context)
