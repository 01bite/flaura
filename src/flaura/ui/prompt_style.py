from __future__ import annotations

from abc import ABC, abstractmethod

from prompt_toolkit.formatted_text import StyleAndTextTuples


class PromptStyle(ABC):
    @abstractmethod
    def in_prompt(self) -> StyleAndTextTuples: ...

    @abstractmethod
    def in2_prompt(self, width: int) -> StyleAndTextTuples: ...

    def out_prompt(self) -> StyleAndTextTuples:
        return []


class DefaultPrompt(PromptStyle):
    def in_prompt(self) -> StyleAndTextTuples:
        return [("class:prompt", "> ")]

    def in2_prompt(self, width: int) -> StyleAndTextTuples:
        return [("class:prompt.dots", "· ".rjust(width))]
