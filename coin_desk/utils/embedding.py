"""
Text embedding utilities using OpenAI API.

Provides functions to generate embeddings and calculate similarity
between texts using OpenAI's text-embedding-3-small model.
Results are cached in SQLite database to reduce API calls.
"""
import logging
import time
from typing import List

import numpy as np
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity

from .embedding_cache import get_cached_embedding, save_embedding

logger = logging.getLogger('coin_desk')

# OpenAI client initialization
try:
    client = OpenAI()  # Automatically picks up OPENAI_API_KEY from environment
except Exception as e:
    logger.warning(f"Failed to initialize OpenAI client: {e}")
    client = None

EMBEDDING_MODEL = "text-embedding-3-small"


def get_embedding(text: str) -> List[float]:
    """
    Get text embedding from OpenAI API or cache.

    Args:
        text: Text to embed.

    Returns:
        Embedding vector as list of floats.

    Raises:
        RuntimeError: If OpenAI client is not initialized.
        Exception: If API request fails.
    """
    if not client:
        raise RuntimeError("OpenAI client not initialized. Check OPENAI_API_KEY.")

    # Check cache first
    cached = get_cached_embedding(text)
    if cached:
        logger.debug("Embedding found in cache")
        return cached

    # Request from API
    try:
        start = time.time()
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
        embedding = response.data[0].embedding
        duration = round(time.time() - start, 2)
        logger.debug(f"Embedding retrieved in {duration}s")

        save_embedding(text, embedding)
        return embedding
    except Exception as e:
        logger.error(f"Failed to get embedding: {e}", exc_info=True)
        raise


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate cosine similarity between two texts.

    Args:
        text1: First text.
        text2: Second text.

    Returns:
        Cosine similarity score (0.0 to 1.0).
    """
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)

    emb1_array = np.array(emb1).reshape(1, -1)
    emb2_array = np.array(emb2).reshape(1, -1)

    start = time.time()
    similarity = float(sk_cosine_similarity(emb1_array, emb2_array)[0][0])
    duration = round(time.time() - start, 2)
    logger.debug(f"Cosine similarity calculated in {duration}s")
    return similarity

