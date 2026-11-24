# -*- coding: utf-8 -*-
"""
成员A · 第1周 流水线入口
------------------------
运行方式：
    cd backend
    python run_pipeline.py

产出：
    output/base_index.json      首批底库索引（文本特征 + 音频指纹）
    output/text_analysis.json    文本比对结果（高亮索引 / 维度分 / 分析标签）
    output/audio_analysis.json   音频指纹比对结果
    frontend/component_data.js   前端组件内嵌数据（供离线 HTML 读取）
"""

import os
import json
import glob
import datetime

from text_features import extract_text_features
from ingest_base import build_index, search_texts, search_audios
from similarity import compare_texts
from audio_fingerprint import fingerprint, generate_demo_wav, make_query_variant

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_TEXT = os.path.join(ROOT, "data", "base_text")
DATA_AUDIO = os.path.join(ROOT, "data", "base_audio")
DATA_QUERY = os.path.join(ROOT, "data", "query")
OUTPUT = os.path.join(ROOT, "output")
FRONTEND = os.path.join(ROOT, "frontend")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def ensure_demo_audio() -> None:
    """底库音频缺失时生成演示 WAV；待测音频由底库变体生成。"""
    if not glob.glob(os.path.join(DATA_AUDIO, "*.wav")):
        generate_demo_wav(os.path.join(DATA_AUDIO, "audio_01_海风云.wav"),
                          base_freq=220.0, seed=11)
        generate_demo_wav(os.path.join(DATA_AUDIO, "audio_02_城市夜跑.wav"),
                          base_freq=330.0, seed=22)
        generate_demo_wav(os.path.join(DATA_AUDIO, "audio_03_改造手记.wav"),
                          base_freq=165.0, seed=33)

    query_audio = os.path.join(DATA_QUERY, "query_录音变体.wav")
    if not os.path.exists(query_audio):
        make_query_variant(
            os.path.join(DATA_AUDIO, "audio_01_海风云.wav"),
            query_audio, stretch=1.05, noise=0.08, seed=1)


def risk_band(score: float) -> dict:
    if score >= 75:
        return {"code": "red", "name": "高风险", "range": "75–100"}
    if score >= 40:
        return {"code": "amber", "name": "需复核", "range": "40–74"}
    return {"code": "green", "name": "低风险", "range": "0–39"}


def run_text_analysis(index: dict) -> dict:
    query_path = sorted(glob.glob(os.path.join(DATA_QUERY, "*.txt")))[0]
    query_text = _read(query_path)
    q_feat = extract_text_features(query_text, idf=index["idf"])

    hits = search_texts(q_feat, index, top_k=3)
    best = hits[0]
    ref_item = next(t for t in index["texts"] if t["item_id"] == best["item_id"])
    ref_text = _read(os.path.join(DATA_TEXT, ref_item["file"]))
    r_feat = extract_text_features(ref_text, idf=index["idf"])

    result = compare_texts(query_text, ref_text, q_feat, r_feat, index["idf"])
    band = risk_band(result["overall_similarity"])

    severity_summary = {"high": 0, "mid": 0, "low": 0}
    for h in result["highlights"]:
        severity_summary[h["severity_code"]] += 1

    analysis = {
        "report_id": f"AIGC-2026-W1-A-{datetime.datetime.now():%H%M%S}",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "member": "A（文本 / 音频算法 + 文本前端组件）",
        "query": {
            "file": os.path.basename(query_path),
            "text": query_text,
            "char_count": q_feat["char_count"],
            "style": q_feat["style"],
        },
        "best_match": {
            "item_id": best["item_id"],
            "file": best["file"],
            "title": best["title"],
            "retrieval_score": best["score"],
            "tfidf_cosine": best["tfidf_cosine"],
            "bigram_jaccard": best["bigram_jaccard"],
        },
        "overall_similarity": result["overall_similarity"],
        "risk_band": band,
        "dimensions": result["dimensions"],
        "highlights": result["highlights"],
        "labels": result["labels"],
        "severity_summary": severity_summary,
        "matched_segment_count": result["matched_segment_count"],
        "metrics": {
            "bigram_jaccard": result["bigram_jaccard"],
            "tfidf_cosine": result["tfidf_cosine"],
            "lcs_coverage": result["lcs_coverage"],
        },
        "retrieval_ranking": hits,
    }
    return analysis


def run_audio_analysis(index: dict) -> dict:
    query_audio = sorted(glob.glob(os.path.join(DATA_QUERY, "*.wav")))[0]
    q_fp = fingerprint(query_audio)
    hits = search_audios(q_fp, index)
    best = hits[0] if hits else None

    label = "音频重合度低"
    if best and best["audio_similarity"] >= 60:
        label = "疑似音频复用"
    elif best and best["audio_similarity"] >= 30:
        label = "音频片段部分重合 · 需复核"

    return {
        "report_id": f"AIGC-2026-W1-AUDIO-{datetime.datetime.now():%H%M%S}",
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "query": {"file": os.path.basename(query_audio),
                  "duration_sec": q_fp["duration_sec"],
                  "hash_count": q_fp["hash_count"]},
        "best_match": best,
        "ranking": hits,
        "label": label,
        "note": "第1周产出指纹比对原型；声纹 / 原声台词维度在第2–3周细化。",
    }


def write_component_data(text_analysis: dict) -> None:
    """把前端组件需要的字段写成 component_data.js（file:// 下可直接加载）。"""
    paragraphs = [p.strip() for p in text_analysis["query"]["text"].split("\n\n") if p.strip()]
    payload = {
        "report_id": text_analysis["report_id"],
        "query_file": text_analysis["query"]["file"],
        "best_match": text_analysis["best_match"],
        "overall_similarity": text_analysis["overall_similarity"],
        "risk_band": text_analysis["risk_band"],
        "dimensions": text_analysis["dimensions"],
        "highlights": text_analysis["highlights"],
        "labels": text_analysis["labels"],
        "severity_summary": text_analysis["severity_summary"],
        "paragraphs": paragraphs,
    }
    os.makedirs(FRONTEND, exist_ok=True)
    js = "// 由 run_pipeline.py 自动生成，请勿手改；重新运行流水线即可刷新\n"
    js += "window.ANALYSIS_DATA = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    with open(os.path.join(FRONTEND, "component_data.js"), "w", encoding="utf-8") as f:
        f.write(js)


def main() -> None:
    os.makedirs(OUTPUT, exist_ok=True)
    ensure_demo_audio()

    index = build_index(DATA_TEXT, DATA_AUDIO, os.path.join(OUTPUT, "base_index.json"))
    print(f"[入库] 文本 {index['text_count']} 篇，音频 {index['audio_count']} 段")

    text_analysis = run_text_analysis(index)
    with open(os.path.join(OUTPUT, "text_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(text_analysis, f, ensure_ascii=False, indent=2)
    print(f"[文本] 综合相似度 {text_analysis['overall_similarity']} · "
          f"高亮 {text_analysis['matched_segment_count']} 处 · "
          f"标签 {len(text_analysis['labels'])} 个")

    audio_analysis = run_audio_analysis(index)
    with open(os.path.join(OUTPUT, "audio_analysis.json"), "w", encoding="utf-8") as f:
        json.dump(audio_analysis, f, ensure_ascii=False, indent=2)
    print(f"[音频] 最佳命中 {audio_analysis['best_match']['file']} · "
          f"相似度 {audio_analysis['best_match']['audio_similarity']} · 标签：{audio_analysis['label']}")

    write_component_data(text_analysis)
    print("[前端] component_data.js 已生成")


if __name__ == "__main__":
    main()
