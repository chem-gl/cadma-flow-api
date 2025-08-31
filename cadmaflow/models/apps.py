from django.apps import AppConfig


class ModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cadmaflow.models'
    label = 'cadmaflow_models'
    verbose_name = 'CADMA Flow Domain Models'

    def ready(self):  # pragma: no cover - import side-effects
        # Ensure provider models registered
        from . import providers  # noqa: F401
        # Register concrete data type models (lives outside models/ package)
        try:  # noqa: WPS501
            from cadmaflow.data_types.qsar import (  # noqa: F401
                AbsorptionData,
                LogPData,
                MutagenicityData,
                ToxicityData,
            )
        except Exception:  # pragma: no cover - defensive
            # Avoid hard failure during early migrations if dependencies missing
            pass
