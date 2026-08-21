from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import SummarizeRequestSerializer
from .services import LLMError, summarize


class HealthView(APIView):
    """Liveness check. Returns 200 if the service is running."""

    def get(self, request):
        return Response({"status": "ok"})


class SummarizeView(APIView):
    """POST text, get a summary with token usage and estimated cost."""

    def post(self, request):
        serializer = SummarizeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = summarize(serializer.validated_data["text"])
        except LLMError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(result)
