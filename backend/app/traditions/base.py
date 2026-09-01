from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TraditionalDesignGrammar(ABC):
    @abstractmethod
    def detect(self, image: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, image: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def reconstruct(self, image: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate(self, grammar: dict[str, Any], parameters: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def validate(self, grammar: dict[str, Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def explain(self, grammar: dict[str, Any]) -> str:
        raise NotImplementedError
