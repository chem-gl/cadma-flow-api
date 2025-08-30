from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .views import HealthView

urlpatterns = [
    path('health/', HealthView.as_view(), name='health'),
    # OpenAPI schema (JSON)
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # Interactive UIs
    path('docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]