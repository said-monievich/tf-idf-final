from collections import defaultdict
import math
from typing import Dict, List
from models import Document


def compute_tf_idf_for_collection(collection_documents: List[Document], all_documents: List[Document]) -> Dict[str, Dict[str, float]]:
    tf = defaultdict(int)
    total_terms = 0

    for doc in collection_documents:
        with open(doc.path, "r", encoding="utf-8") as f:
            words = f.read().lower().split()
        total_terms += len(words)
        for word in words:
            tf[word] += 1

    tf_normalized = {word: count / total_terms for word, count in tf.items()}

    N = len(all_documents)
    df = defaultdict(int)

    for doc in all_documents:
        with open(doc.path, "r", encoding="utf-8") as f:
            unique_terms = set(f.read().lower().split())
        for term in unique_terms:
            df[term] += 1

    idf = {
        term: math.log(N / df[term])
        for term in tf.keys() if df[term] > 0
    }

    return {
        "tf": tf_normalized,
        "idf": idf
    }

