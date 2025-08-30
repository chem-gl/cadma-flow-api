from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Simple health check endpoint.

    Returns a JSON payload with service status. Useful for uptime checks.
    """

    @extend_schema(
        operation_id="health_check",
        summary="Health check",
        description="Devuelve el estado básico del servicio para monitoreo.",
        responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
        tags=["Health"],
    )
    def get(self, _request):  # noqa: D401
        return Response({"status": "ok"})