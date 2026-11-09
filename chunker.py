
def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be between 0 and chunk_size")

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        # Prefer a whitespace boundary at the end.
        if end < text_length:
            boundary = max(
                text.rfind(" ", start, end),
                text.rfind("\n", start, end),
                text.rfind("\t", start, end),
            )

            if boundary > start + int(chunk_size * 0.6):
                end = boundary

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        # Calculate the next starting point using overlap.
        next_start = max(start + 1, end - overlap)

        # If the position is inside a word, advance to its end.
        if (
            next_start > 0
            and not text[next_start - 1].isspace()
        ):
            while (
                next_start < text_length
                and not text[next_start].isspace()
            ):
                next_start += 1

        # Skip whitespace to begin at the next word.
        while (
            next_start < text_length
            and text[next_start].isspace()
        ):
            next_start += 1

        start = next_start

    return chunks
