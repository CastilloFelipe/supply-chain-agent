"""Capa LLM: traduce preguntas de negocio a escenarios what-if del modelo de red."""

from .translator import TranslatedScenario, TranslationError, translate

__all__ = ["TranslatedScenario", "TranslationError", "translate"]
