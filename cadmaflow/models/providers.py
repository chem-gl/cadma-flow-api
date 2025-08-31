# molecules/providers.py
"""
Sistema de proveedores de datos moleculares.

Propósito:
- Gestionar diferentes programas y métodos que calculan propiedades moleculares
- Permitir la ejecución de múltiples cálculos en una sola ejecución
- Registrar la procedencia de los datos calculados
"""

import uuid

from django.db import models

from cadmaflow.models.choices import StatusChoices


class DataProvider(models.Model):
    """
    Representa un programa o método que puede calcular múltiples propiedades.
    
    Propósito:
    - Modelar software externo o métodos internos que calculan propiedades
    - Definir qué propiedades puede calcular cada proveedor
    - Configurar cómo ejecutar cada proveedor
    
    Ejemplos: T.E.S.T., AMBIT, ProTox, Gaussian, etc.
    """
    
    # Identificación del proveedor
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    
    # Propiedades que este proveedor puede calcular
    calculable_properties = models.JSONField(
        default=list,
        help_text="Lista de propiedades que este proveedor puede calcular"
    )
    
    # Configuración de ejecución
    execution_command = models.TextField(help_text="Comando para ejecutar este proveedor")
    input_format = models.CharField(max_length=50, help_text="Formato de entrada esperado")
    output_format = models.CharField(max_length=50, help_text="Formato de salida esperado")
    
    # Estado del proveedor
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} v{self.version}"


class ProviderExecution(models.Model):
    """
    Registra una ejecución específica de un proveedor de datos.
    
    Propósito:
    - Trackear cada ejecución de un proveedor
    - Almacenar parámetros y resultados de la ejecución
    - Servir como referencia de procedencia para los datos calculados
    """
    
    # Identificador único de la ejecución
    execution_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relación con el proveedor
    provider = models.ForeignKey(DataProvider, on_delete=models.CASCADE, related_name='executions')
    
    # Propiedades calculadas en esta ejecución
    calculated_properties = models.JSONField(
        default=list,
        help_text="Propiedades calculadas en esta ejecución"
    )
    
    # Moléculas procesadas
    molecules = models.ManyToManyField('Molecule', related_name='provider_executions')
    
    # Configuración y parámetros usados
    execution_parameters = models.JSONField(
        default=dict,
        help_text="Parámetros específicos usados en esta ejecución"
    )
    
    # Resultados de la ejecución
    results = models.JSONField(
        default=dict,
        help_text="Resultados brutos de la ejecución"
    )
    
    # Estado de la ejecución
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.provider.name} - {self.execution_id}"