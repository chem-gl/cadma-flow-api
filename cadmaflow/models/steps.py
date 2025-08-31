# molecules/steps.py
"""
Implementación de pasos del workflow molecular.

Propósito:
- Definir la estructura base para todos los pasos del workflow
- Implementar la lógica común de ejecución de pasos
- Proporcionar hooks para personalización de pasos específicos
"""

from abc import ABC, abstractmethod

from django.utils import timezone

from cadmaflow.models.choices import StatusChoices


class BaseStep(ABC):
    """
    Clase abstracta base para todos los steps del workflow.
    
    Propósito:
    - Definir la interfaz común que todos los pasos deben implementar
    - Proporcionar funcionalidad base para ejecución y tracking
    - Gestionar la adquisición y procesamiento de datos
    
    Características:
    - Cada step debe definir sus requisitos de datos y resultados esperados
    - Implementa el patrón Template Method para ejecución de pasos
    - Proporciona hooks para personalización en subclases
    """
    
    # Metadata del step (debe ser definida por las subclases)
    step_id: str
    name: str
    description: str
    order: int
    
    # Configuración de datos (debe ser definida por las subclases)
    required_data_classes: list  # Clases de datos requeridas
    produced_data_classes: list  # Clases de datos producidas
    
    # Configuración de ejecución
    allows_branching: bool = False  # Si permite crear ramas
    parameters_schema: dict = {}    # Esquema de parámetros válidos
    
    @abstractmethod
    def execute(self, step_execution, parameters=None):
        """
        Ejecuta el step usando los datos congelados en la step_execution.
        
        Args:
            step_execution: Ejecución del paso con datos de entrada congelados
            parameters: Parámetros específicos para esta ejecución
        
        Returns:
            Diccionario con resultados de la ejecución
        """
        # Obtener datos de entrada congelados
        input_data = step_execution.input_data_snapshot
        
        # Procesar el step (implementación específica)
        results = self._process_step(input_data, step_execution, parameters or {})
        
        # Guardar resultados
        step_execution.results = results
        step_execution.status = StatusChoices.COMPLETED
        step_execution.completed_at = timezone.now()
        step_execution.save()
        
        return results
    
    @abstractmethod
    def _process_step(self, input_data, step_execution, parameters):
        """
        Procesamiento específico del step (debe ser implementado por subclases).
        
        Args:
            input_data: Datos de entrada congelados organizados por molécula
            step_execution: Ejecución del paso
            parameters: Parámetros específicos para esta ejecución
        
        Returns:
            Resultados del procesamiento
        """
        raise NotImplementedError("Las subclases deben implementar este método")
    
    def can_execute(self, execution):
        """
        Verifica si el step puede ejecutarse en la ejecución dada.
        
        Args:
            execution: Ejecución de workflow
        
        Returns:
            True si todas las dependencias están satisfechas
        """
        # Verificar que todas las familias tengan los datos requeridos
        for family in execution.families.all():
            for data_class in self.required_data_classes:
                for _ in family.members.all():
                    method = execution.get_data_retrieval_method(family.family_id, data_class.__name__)
                    if not method:
                        return False  # No hay método configurado para este dato en esta familia
        return True
    
    def get_progress(self, execution):
        """
        Calcula el progreso de preparación para este step en todas las familias.
        
        Args:
            execution: Ejecución de workflow
        
        Returns:
            Porcentaje de completitud (0.0 a 1.0)
        """
        total_required = 0
        completed = 0
        
        for family in execution.families.all():
            for _ in family.members.all():
                for data_class in self.required_data_classes:
                    total_required += 1
                    method = execution.get_data_retrieval_method(family.family_id, data_class.__name__)
                    if method:
                        completed += 1
        
        return completed / total_required if total_required > 0 else 1.0