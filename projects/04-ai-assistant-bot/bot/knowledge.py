"""База знаний: текстовый файл, разбитый на блоки, и простой поиск по словам.

Файл делится на блоки пустыми строками. Один блок — один факт или один вопрос с ответом.
Поиск без нейросетей: слова приводятся к грубой «основе» (отбрасываем окончания)
и блоки ранжируются по числу совпавших слов, редкие слова весят больше.
"""
import math
import re
from pathlib import Path

STOP_WORDS = {
    "как", "что", "это", "для", "или", "при", "вы", "мы", "там", "тут", "ещё", "еще", "уже",
    "вас", "вам", "нас", "нам", "мне", "ваш", "наш", "все", "всё", "его", "ее", "её", "они",
    "есть", "быть", "можно", "нужно", "если", "когда", "где", "какой", "какая", "какие",
    "сколько", "почему", "будет", "был", "была", "были", "ли", "же", "бы", "не", "ни", "на",
    "по", "из", "от", "до", "за", "со", "во", "об", "про", "над", "под", "без", "а", "и", "в", "с", "к", "у", "о",
    "привет", "здравствуйте", "добрый", "день", "пожалуйста", "подскажите", "скажите",
}

# Окончания, которые отбрасываем (длинные — первыми)
SUFFIXES = sorted(
    [
        "ться", "ется", "ются", "ешь", "ишь", "ать", "ять", "ить", "еть", "ами", "ями", "ого", "его",
        "ому", "ему", "ыми", "ими", "ов", "ев", "ей", "ом", "ем", "ам", "ям", "ах", "ях", "ую", "юю",
        "ая", "яя", "ое", "ее", "ые", "ие", "ых", "их", "ий", "ый", "ой", "ек", "ик", "ет", "ит",
        "ут", "ют", "ат", "ят", "ть", "ся", "а", "я", "у", "ю", "ы", "и", "е", "о", "ь", "й",
    ],
    key=len,
    reverse=True,
)


def stem(word: str) -> str:
    """Грубая «основа» слова: без окончания и не длиннее 5 букв (находится / находитесь -> наход)."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    return word[:5]


def stems(text: str) -> set[str]:
    words = re.findall(r"[a-zа-я0-9]+", text.lower().replace("ё", "е"))
    return {stem(w) for w in words if len(w) > 2 and w not in STOP_WORDS}


class KnowledgeBase:
    def __init__(self, text: str):
        blocks = [b.strip() for b in re.split(r"\n\s*\n", text)]
        # строки-комментарии (начинаются с #) в поиске не участвуют
        self.chunks = [b for b in blocks if b and not b.startswith("#")]
        self._stems = [stems(chunk) for chunk in self.chunks]

        # «вес» слова: чем реже встречается по блокам, тем оно важнее
        total = len(self.chunks)
        document_frequency: dict[str, int] = {}
        for chunk_stems in self._stems:
            for s in chunk_stems:
                document_frequency[s] = document_frequency.get(s, 0) + 1
        self._weight = {s: math.log(1 + total / df) for s, df in document_frequency.items()}

    @classmethod
    def from_file(cls, path: Path) -> "KnowledgeBase":
        if not path.exists():
            raise SystemExit(f"Файл базы знаний не найден: {path}")
        return cls(path.read_text(encoding="utf-8"))

    def search(self, query: str, limit: int = 4) -> list[str]:
        """Самые подходящие блоки для запроса (пустой список, если совпадений нет)."""
        query_stems = stems(query)
        scored = []
        for chunk, chunk_stems in zip(self.chunks, self._stems):
            score = sum(self._weight[s] for s in query_stems & chunk_stems)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:limit]]
