from django.db import models


class SourceChoices(models.TextChoices):
    """Opciones para el origen de los datos moleculares"""
    USER = 'USER', 'Usuario'
    TEST = 'TEST', 'T.E.S.T.'
    AMBIT = 'AMBIT', 'AMBIT'
    PROTOX = 'PROTOX', 'ProTox'
    DRUGBILITY = 'DRUGBILITY', 'Drugbility'
    GAUSSIAN = 'GAUSSIAN', 'Gaussian'
    EXPERIMENTAL = 'EXPERIMENTAL', 'Experimental'
    OTHER = 'OTHER', 'Otro'

class NativeTypeChoices(models.TextChoices):
    """Opciones para tipos de datos nativos"""
    FLOAT = 'FLOAT', 'Número decimal'
    INTEGER = 'INTEGER', 'Número entero'
    BOOLEAN = 'BOOLEAN', 'Valor booleano'
    STRING = 'STRING', 'Texto'
    LIST = 'LIST', 'Lista de valores'
    DICT = 'DICT', 'Diccionario/objeto'
    COMPLEX = 'COMPLEX', 'Tipo complejo personalizado'

class StatusChoices(models.TextChoices):
    """Opciones para estados de ejecución"""
    PENDING = 'PENDING', 'Pendiente'
    RUNNING = 'RUNNING', 'Ejecutando'
    COMPLETED = 'COMPLETED', 'Completado'
    FAILED = 'FAILED', 'Fallido'
    DATA_FROZEN = 'DATA_FROZEN', 'Datos Congelados'