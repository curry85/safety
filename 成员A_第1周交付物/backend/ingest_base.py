# -*- coding: utf-8 -*-
"""
首批底库数据整理与入库模块（成员A · 第1周）
--------------------------------------------
职责：
  - 扫描 data/base_text 与 data/base_audio；
  - 抽取文本特征 / 音频指纹，写入 output/base_index.json；
  - 提供本地 brute-force 检索接口。

预留：FAISS 底库底层接口由成员C统一搭建；接入时把 search_texts 内的
本地余弦计算替换为 FAISS 向量检索即可，上层 pipeline 无需改动。
"""

import os
import json
import datetime

from text_features import extract_text_features, build_idf
from audio_fingerprint import fingerprint
from similarity import cosine, jaccard


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def ingest_texts(base_dir: str) -> tuple[list[dict], dict[str, float]]:
    """入库全部底库文本，返回条目列表与 IDF 表。"""
    files = sorted(f for f in os.listdir(base_dir) if f.endswith(".txt"))
    raw_docs = [_read(os.path.join(base_dir, f)) for f in files]
    docs_tokens = [extract_text_features(d)["tokens"] for d in raw_docs]
    idf = build_idf(docs_tokens)

    items = []
    for idx, (fname, doc) in enumerate(zip(files, raw_docs), start=1):
        feat = extract_text_features(doc, idf=idf)
        title = doc.splitlines()[0].strip() if doc.strip() else fname
        items.append({
            "item_id": f"T{idx:03d}",
            "file": fname,
            "title": title,
            "features": {
                "char_count": feat["char_count"],
                "token_set": feat["token_set"],
                "bigram_set": feat["bigram_set"],
                "tfidf": feat["tfidf"],
                "style": feat["style"],
            },
        })
    return items, idf


def ingest_audios(audio_dir: str) -> list[dict]:
    """入库全部底库音频指纹。"""
    items = []
    files = sorted(f for f in os.listdir(audio_dir) if f.endswith(".wav"))
    for idx, fname in enumerate(files, start=1):
        fp = fingerprint(os.path.join(audio_dir, fname))
        items.append({
            "item_id": f"A{idx:03d}",
            "file": fname,
            "fingerprint": fp,
        })
    return items


def build_index(text_dir: str, audio_dir: str, index_path: str) -> dict:
    """整理首批底库并落盘索引 JSON。"""
    text_items, idf = ingest_texts(text_dir)
    audio_items = ingest_audios(audio_dir)

    index = {
        "version": "week1-memberA",
        "built_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "text_count": len(text_items),
        "audio_count": len(audio_items),
        "idf": idf,
        "texts": text_items,
        "audios": audio_items,
        "faiss_hook": {
            "status": "pending",
            "note": "FAISS 向量索引由成员C提供底层接口；当前为本地 JSON brute-force 检索。"
        },
    }
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return index


def search_texts(query_feat: dict, index: dict, top_k: int = 3) -> list[dict]:
    """
    文本检索：TF-IDF 余弦为主，二元组 Jaccard 为辅，返回 Top-K 命中。
    TODO(成员C)：替换为 FAISS 向量检索（索引库搭建完成后启用）。
    """
    ranked = []
    for item in index["texts"]:
        tfidf_cos = cosine(query_feat.get("tfidf", {}), item["features"]["tfidf"])
        bigram_jac = jaccard(query_feat["bigram_set"], item["features"]["bigram_set"])
        score = 0.6 * tfidf_cos + 0.4 * bigram_jac
        ranked.append({
            "item_id": item["item_id"],
            "file": item["file"],
            "title": item["title"],
            "score": round(score, 4),
            "tfidf_cosine": round(tfidf_cos, 4),
            "bigram_jaccard": round(bigram_jac, 4),
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]


def search_audios(query_fp: dict, index: dict) -> list[dict]:
    """音频检索：指纹哈希比对，返回按相似度排序的命中列表。"""
    from audio_fingerprint import compare_fingerprints
    ranked = []
    for item in index["audios"]:
        sim = compare_fingerprints(query_fp, item["fingerprint"])
        ranked.append({
            "item_id": item["item_id"],
            "file": item["file"],
            **sim,
        })
    ranked.sort(key=lambda x: x["audio_similarity"], reverse=True)
    return ranked
