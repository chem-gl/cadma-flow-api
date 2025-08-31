"""Domain models package for CADMA Flow.

Mantiene los modelos de dominio (moléculas, familias, workflow, providers).
Se minimizan importaciones tempranas para evitar AppRegistryNotReady durante
``django.setup()``. Use imports explícitos donde se necesiten las clases.

AppConfig: ``cadmaflow.models.apps.ModelsConfig``
"""

__all__ = [
	# listado informativo (sin cargar realmente los modelos aquí)
]
