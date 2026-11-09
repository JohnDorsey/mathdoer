"""Text of a run's output, bounded so a runaway program cannot fill memory."""
from collections import deque

DEFAULT_MAXIMUM_CHARACTER_COUNT = 1_000_000


class OutputBuffer:
    """Keeps the newest characters; when it overflows the oldest text is discarded."""

    def __init__(self, maximum_character_count: int = DEFAULT_MAXIMUM_CHARACTER_COUNT):
        if maximum_character_count < 1:
            raise ValueError("maximum_character_count must be at least 1")
        self.maximum_character_count = maximum_character_count
        self.clear()

    def clear(self) -> None:
        self._chunks = deque()
        self._character_count = 0
        self.discarded_character_count = 0

    def append(self, text: str) -> None:
        if not text:
            return
        if len(text) >= self.maximum_character_count:
            self.discarded_character_count += (
                self._character_count + len(text) - self.maximum_character_count
            )
            self._chunks = deque([text[-self.maximum_character_count:]])
            self._character_count = self.maximum_character_count
            return
        self._chunks.append(text)
        self._character_count += len(text)
        self._discard_oldest(self._character_count - self.maximum_character_count)

    def _discard_oldest(self, count: int) -> None:
        while count > 0:
            oldest = self._chunks[0]
            if len(oldest) <= count:
                self._chunks.popleft()
                dropped = len(oldest)
            else:
                self._chunks[0] = oldest[count:]
                dropped = count
            count -= dropped
            self._character_count -= dropped
            self.discarded_character_count += dropped

    @property
    def text(self) -> str:
        return "".join(self._chunks)

    @property
    def truncated(self) -> bool:
        return self.discarded_character_count > 0

    def __len__(self) -> int:
        return self._character_count
