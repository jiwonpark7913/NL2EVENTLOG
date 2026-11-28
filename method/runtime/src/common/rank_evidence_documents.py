"""Parallel BM25, character cosine and optional sentence embeddings with RRF."""

from __future__ import annotations
from collections import Counter
import math
import re
from src.common.schema_metadata import normalize


def word_tokens(value):
    """PURPOSE: Tokenize identifiers and multilingual text for sparse retrieval.
    INPUT: Arbitrary label, description or query.
    OUTPUT: Normalized word tokens including compact identifier fragments.
    """
    normalized = normalize(str(value))
    tokens = normalized.split()
    compact = ''.join(tokens)
    return [*tokens, *([compact] if compact and compact not in tokens else [])]


def character_ngrams(value, sizes=(2, 3, 4)):
    """PURPOSE: Represent misspellings and Korean/English surface variants locally.
    INPUT: Text and n-gram sizes.
    OUTPUT: Character n-grams over whitespace-free normalized text.
    """
    compact = re.sub(r'\s+', '', normalize(str(value)))
    return [compact[index:index + size] for size in sizes
            for index in range(max(0, len(compact) - size + 1))]


def bm25_scores(query, documents, *, k1=1.2, b=.75):
    """PURPOSE: Rank candidate documents with deterministic BM25.
    INPUT: Query and list of document strings.
    OUTPUT: One nonnegative BM25 score per document.
    """
    tokenized = [word_tokens(document) for document in documents]
    query_terms = list(dict.fromkeys(word_tokens(query)))
    average = sum(map(len, tokenized)) / len(tokenized) if tokenized else 0.0
    document_frequency = {
        term: sum(term in set(tokens) for tokens in tokenized)
        for term in query_terms}
    scores = []
    for tokens in tokenized:
        counts = Counter(tokens)
        length_norm = 1 - b + b * len(tokens) / average if average else 1.0
        score = 0.0
        for term in query_terms:
            frequency = counts[term]
            if not frequency:
                continue
            inverse = math.log(1 + (len(tokenized) - document_frequency[term] + .5) /
                               (document_frequency[term] + .5))
            score += inverse * frequency * (k1 + 1) / (frequency + k1 * length_norm)
        scores.append(score)
    return scores


def cosine_scores(query, documents):
    """PURPOSE: Rank surface similarity with TF-IDF character n-gram cosine.
    INPUT: Query and candidate document strings.
    OUTPUT: One cosine score in [0,1] per document; no external embedding call.
    """
    vectors = [Counter(character_ngrams(document)) for document in documents]
    query_vector = Counter(character_ngrams(query))
    features = set(query_vector)
    for vector in vectors:
        features.update(vector)
    document_frequency = {
        feature: sum(feature in vector for vector in vectors)
        for feature in features}
    idf = {feature: math.log((len(vectors) + 1) /
                             (document_frequency[feature] + 1)) + 1
           for feature in features}
    weighted_query = {feature: count * idf[feature]
                      for feature, count in query_vector.items()}
    query_norm = math.sqrt(sum(value * value for value in weighted_query.values()))
    result = []
    for vector in vectors:
        weighted = {feature: count * idf[feature] for feature, count in vector.items()}
        norm = math.sqrt(sum(value * value for value in weighted.values()))
        dot = sum(weighted_query.get(feature, 0.0) * value
                  for feature, value in weighted.items())
        result.append(dot / (query_norm * norm) if query_norm and norm else 0.0)
    return result


def reciprocal_rank_fusion(rankings, *, constant=60):
    """PURPOSE: Fuse independent retrieval ranks without score calibration.
    INPUT: Rankings as ordered candidate-ID lists and an RRF constant.
    OUTPUT: Candidate-ID to RRF score mapping.
    """
    scores = Counter()
    for ranking in rankings:
        for rank, candidate_id in enumerate(ranking, 1):
            scores[candidate_id] += 1.0 / (constant + rank)
    return dict(scores)


def semantic_scores(query, documents, encoder):
    """PURPOSE: Compare meaning independently of lexical candidate matching.
    INPUT: Query, document strings and an encoder with encode(list[str]) -> numeric vectors.
    OUTPUT: Cosines in [-1,1]; malformed/nonfinite vectors raise ValueError, with no lexical gate.
    """
    vectors = [list(map(float, vector)) for vector in encoder.encode([query, *documents])]
    if (len(vectors) != len(documents) + 1 or not vectors[0] or
            any(len(v) != len(vectors[0]) or not all(map(math.isfinite, v)) for v in vectors)):
        raise ValueError('invalid_semantic_embedding_vectors')
    norms = [math.sqrt(sum(x*x for x in vector)) for vector in vectors]
    return [max(-1.0, min(1.0, sum(a*b for a, b in zip(vectors[0], vector)) /
                         (norms[0]*norm))) if norms[0] and norm else 0.0
            for vector, norm in zip(vectors[1:], norms[1:])]


def rank_documents(query, documents, *, method='hybrid', encoder=None, semantic_min_score=.35):
    """PURPOSE: Retrieve broad candidate recall before categorical selection.
    INPUT: Query, unique id/text records, bm25/cosine/semantic/hybrid mode and optional encoder.
    OUTPUT: Copied records with component scores/ranks and RRF; sparse calls preserve prior ordering.
    """
    if method not in ('bm25', 'cosine', 'semantic', 'hybrid'):
        raise ValueError('method must be bm25, cosine, semantic or hybrid')
    if method == 'semantic' and encoder is None:
        raise ValueError('semantic retrieval requires an encoder')
    if not -1 <= semantic_min_score <= 1:
        raise ValueError('semantic_min_score must be in [-1,1]')
    if not documents:
        return []
    texts = [record['text'] for record in documents]
    if len({record['id'] for record in documents}) != len(documents):
        raise ValueError('retrieval_document_ids_must_be_unique')
    bm25 = bm25_scores(query, texts)
    cosine = cosine_scores(query, texts)
    dense = semantic_scores(query, texts, encoder) if encoder is not None else None
    components = {'bm25': bm25, 'cosine': cosine}
    if dense is not None:
        components['semantic'] = dense
    rankings = {}
    for name, scores in components.items():
        minimum = semantic_min_score if name == 'semantic' else 0
        indices = sorted((i for i, score in enumerate(scores) if score > 0 and score >= minimum),
                         key=lambda i: (-scores[i], documents[i]['id']))
        rankings[name] = {documents[i]['id']: rank for rank, i in enumerate(indices, 1)}
    fused = reciprocal_rank_fusion([list(ranking) for ranking in rankings.values()])
    result = []
    for index, record in enumerate(documents):
        item = dict(record)
        item['similarity'] = {
            'bm25': bm25[index], 'cosine': cosine[index],
            'semantic': dense[index] if dense is not None else None,
            'bm25_rank': rankings['bm25'].get(record['id']),
            'cosine_rank': rankings['cosine'].get(record['id']),
            'semantic_rank': rankings.get('semantic', {}).get(record['id']),
            'rrf': fused.get(record['id'], 0.0)}
        result.append(item)
    if method != 'hybrid':
        return sorted(result, key=lambda item: (-item['similarity'][method], item['id']))
    return sorted(result, key=lambda item: (-item['similarity']['rrf'],
                  -item['similarity']['cosine'], -item['similarity']['bm25'], item['id']))
