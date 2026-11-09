"""Standalone component test for embedding generation."""

import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from embedder import generate_embeddings, get_embedding_dimension


def main():
    sample_texts = [
        "Infosys is a global leader in next-generation digital services and consulting.",
        "Consolidated revenue grew by 4.7% in constant currency terms.",
        "Operating margin was 21.1% for the full fiscal year.",
    ]

    print("Testing embedding generation with sample texts...")
    embeddings = generate_embeddings(sample_texts)

    dim = get_embedding_dimension()
    assert len(embeddings) == 3, f"Expected 3 embeddings, got {len(embeddings)}"
    assert len(embeddings[0]) == dim, f"Expected dimension {dim}, got {len(embeddings[0])}"

    print(f"Generated {len(embeddings)} vectors of dimension {dim}.")
    print("Embedding test passed!")


if __name__ == "__main__":
    main()

