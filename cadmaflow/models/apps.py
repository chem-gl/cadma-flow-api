from django.apps import AppConfig


class ModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cadmaflow.models'
    verbose_name = 'CADMA Flow Domain Models'

    def ready(self):  # pragma: no cover - import side effects only
        """Carga perezosa de módulos de providers para registrar lógica dinámica."""
        try:  # Imports suaves: pueden faltar en etapas tempranas
            import importlib
            importlib.import_module('cadmaflow.models.qsar_properties')  # registra subclases
            importlib.import_module('cadmaflow.models.providers')        # asegura ProviderExecution
            importlib.import_module('cadmaflow.providers.reference')
            importlib.import_module('cadmaflow.providers.qsar')
        except Exception:  # noqa: BLE001
            pass
