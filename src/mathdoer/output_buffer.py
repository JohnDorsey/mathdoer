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
        self._chunks = deque()  # of (text, is_error)
        self._character_count = 0
        self.discarded_character_count = 0

    def append(self, text: str, is_error: bool = False) -> str:
        """Add text. Returns the text this discarded from the beginning, or an empty string."""
        if not text:
            return ""
        cap = self.maximum_character_count
        if len(text) >= cap:
            discarded = self.text + text[: len(text) - cap]
            self.discarded_character_count += len(discarded)
            self._chunks = deque([(text[len(text) - cap:], is_error)])
            self._character_count = cap
            return discarded
        self._chunks.append((text, is_error))
        self._character_count += len(text)
        return self._discard_oldest(self._character_count - cap)

    def _discard_oldest(self, count: int) -> str:
        discarded_pieces = []
        while count > 0:
            oldest_text, is_error = self._chunks[0]
            if len(oldest_text) <= count:
                self._chunks.popleft()
                piece = oldest_text
            else:
                piece = oldest_text[:count]
                self._chunks[0] = (oldest_text[count:], is_error)
            discarded_pieces.append(piece)
            count -= len(piece)
            self._character_count -= len(piece)
            self.discarded_character_count += len(piece)
        return "".join(discarded_pieces)

    @property
    def text(self) -> str:
        return "".join(text for text, _ in self._chunks)

    @property
    def segments(self) -> tuple[tuple[str, bool], ...]:
        """The text as (text, is_error) runs, neighbours of the same kind merged."""
        runs: list[list] = []
        for text, is_error in self._chunks:
            if runs and runs[-1][1] == is_error:
                runs[-1][0] += text
            else:
                runs.append([text, is_error])
        return tuple((text, is_error) for text, is_error in runs)

    @property
    def truncated(self) -> bool:
        return self.discarded_character_count > 0

    def __len__(self) -> int:
        return self._character_count
