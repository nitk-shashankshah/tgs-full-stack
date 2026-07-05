import os


def get_embedding(text: str):
    """
    Returns a 1024-dimension embedding via Voyage AI.
    Returns None when VOYAGE_API_KEY is not set (test mode).
    """
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key or api_key == "test":
        return None

    import voyageai
    client = voyageai.Client(api_key=api_key)
    result = client.embed([text], model="voyage-large-2")
    return result.embeddings[0]


def build_product_text(product: dict) -> str:
    parts = [
        product.get("product_name", ""),
        product.get("description", ""),
        product.get("category", ""),
        " ".join(product.get("features", []) or []),
        " ".join(product.get("ideal_keywords", []) or []),
    ]
    return " ".join(p for p in parts if p).strip()
