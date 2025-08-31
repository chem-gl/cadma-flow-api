"""Domain models package for CADMA Flow.

Mantiene los modelos de dominio (moléculas, familias, workflow, providers).
Se minimizan importaciones tempranas para evitar AppRegistryNotReady durante
``django.setup()``. Use imports explícitos donde se necesiten las clases.

AppConfig: ``cadmaflow.models.apps.ModelsConfig``
"""

__all__ = [
	# listado informativo (sin cargar realmente los modelos aquí)
]

# Asegurar registro de modelos definidos fuera de models.py
# (Django sólo auto-detecta los modelos en models.py; los adicionales
# deben importarse para que el AppRegistry los registre antes de las
# comprobaciones de relaciones en migraciones / system checks.)
try:  # pragma: no cover - import side-effect
	from .providers import DataProvider, ProviderExecution  # noqa: F401
except Exception:  # pragma: no cover - fallo silencioso en import temprano
	# En escenarios de inicialización parcial (por ejemplo, importando
	# sólo para lectura de metadatos) se puede ignorar; Django hará el
	# import completo durante setup().
	pass

