from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from .serializers import (
    RewriteRequestSerializer,
    SummarizeRequestSerializer,
    TranslateRequestSerializer,
)
from .services import LLMError, rewrite, summarize, translate


class LLMThrottle(AnonRateThrottle):
    scope = "llm"


class HealthView(APIView):
    """Liveness check. Returns 200 if the service is running."""

    throttle_classes = []

    def get(self, request):
        return Response({"status": "ok"})


class LLMView(APIView):
    """Validate, call a service, translate provider failure into a 503."""

    throttle_classes = [LLMThrottle]
    serializer_class = None

    def run(self, data):
        raise NotImplementedError

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = self.run(serializer.validated_data)
        except LLMError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(result)


class SummarizeView(LLMView):
    serializer_class = SummarizeRequestSerializer

    def run(self, data):
        return summarize(data["text"])


class RewriteView(LLMView):
    serializer_class = RewriteRequestSerializer

    def run(self, data):
        return rewrite(data["text"], data["tone"])


class TranslateView(LLMView):
    serializer_class = TranslateRequestSerializer

    def run(self, data):
        return translate(data["text"], data["target_language"])
