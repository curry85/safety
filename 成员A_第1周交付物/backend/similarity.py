# -*- coding: utf-8 -*-
"""
文本 / 音频相似度比对模块（成员A · 第1周）
------------------------------------------
文本：
  - TF-IDF 余弦相似度；
  - 字二元组 Jaccard 相似度；
  - 句子级对齐 + 句内字符公共片段抽取，带字符级偏移索引；
  - 四个文本维度评分（行文习惯 / 故事剧情 / 人物设定 / 专属名词）；
  - 初步分析标签规则（疑似洗稿 / 段落级复制 等，第3周再由规则引擎细化）。

音频：指纹哈希集合比对，实现见 audio_fingerprint.py。
"""

import difflib
import re

# ---- 维度关键词表（演示语料规模小，规则可解释；后续可替换为实体识别模型） ----
PLOT_WORDS = ["信", "航标", "码头", "船", "灯塔", "潮水", "海风", "长堤", "港口", "雾港"]
CHARACTER_WORDS = ["守塔人", "听力", "灯光", "呼唤", "他", "守塔"]


def cosine(vec_a: dict, vec_b: dict) -> float:
    """字典向量余弦相似度，返回 0~1。"""
    if not vec_a or not vec_b:
        return 0.0
    common = set(vec_a) & set(vec_b)
    dot = sum(vec_a[k] * vec_b[k] for k in common)
    na = sum(v * v for v in vec_a.values()) ** 0.5
    nb = sum(v * v for v in vec_b.values()) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def jaccard(set_a: list[str] | set, set_b: list[str] | set) -> float:
    a, b = set(set_a), set(set_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def _split_sents(paragraph: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[。！？!?；;])", paragraph) if s.strip()]


def _sentence_locations(text: str) -> list[dict]:
    """切分句子并记录全局字符偏移、段落 / 句子下标。"""
    paragraphs = _split_paragraphs(text)
    locs = []
    cursor = 0
    for p_idx, para in enumerate(paragraphs):
        para_start = text.find(para, cursor)
        sents = _split_sents(para)
        sc = para_start
        for s_idx, sent in enumerate(sents):
            s_start = text.find(sent, sc)
            locs.append({
                "paragraph_index": p_idx + 1,
                "sentence_index": s_idx + 1,
                "paragraph": para,
                "sentence": sent,
                "start": s_start,
                "end": s_start + len(sent),
            })
            sc = s_start + len(sent)
        cursor = para_start + len(para)
    return locs


def _char_common_blocks(q_sent: str, r_sent: str, min_len: int = 6) -> list[dict]:
    """句内字符级公共片段。"""
    matcher = difflib.SequenceMatcher(None, q_sent, r_sent, autojunk=False)
    blocks = []
    for block in matcher.get_matching_blocks():
        if block.size < min_len:
            continue
        blocks.append({
            "text": q_sent[block.a : block.a + block.size],
            "q_start": block.a,
            "q_end": block.a + block.size,
            "r_start": block.b,
            "r_end": block.b + block.size,
            "length": block.size,
        })
    return blocks


def find_common_segments(query: str, reference: str, min_len: int = 6) -> list[dict]:
    """
    句子级对齐后抽取公共片段，返回带双方字符偏移的片段列表。
    偏移为全局字符下标（含标点），前端可直接按 start/end 切片高亮。
    第 1 段（标题行）不参与比对。
    """
    q_locs = _sentence_locations(query)
    r_locs = _sentence_locations(reference)
    q_sents = [l["sentence"] for l in q_locs]
    r_sents = [l["sentence"] for l in r_locs]

    matcher = difflib.SequenceMatcher(None, q_sents, r_sents, autojunk=False)
    segments = []
    for block in matcher.get_matching_blocks():
        for k in range(block.size):
            q_loc = q_locs[block.a + k]
            r_loc = r_locs[block.b + k]
            if q_loc["paragraph_index"] == 1:  # 跳过标题行
                continue
            blocks = _char_common_blocks(q_loc["sentence"], r_loc["sentence"], min_len)
            if not blocks:
                continue
            first, last = blocks[0], blocks[-1]
            rel_start = first["q_start"]
            rel_end = last["q_end"]
            seg_text = q_loc["sentence"][rel_start:rel_end]
            if len(re.sub(r"[\s，。！？；、“”‘’（）《》—…]", "", seg_text)) < min_len:
                continue
            segments.append({
                "text": seg_text,
                "query_start": q_loc["start"] + rel_start,
                "query_end": q_loc["start"] + rel_end,
                "ref_start": r_loc["start"] + first["r_start"],
                "ref_end": r_loc["start"] + last["r_end"],
                "length": len(seg_text),
                "paragraph_index": q_loc["paragraph_index"],
                "sentence_index": q_loc["sentence_index"],
                "paragraph": q_loc["paragraph"],
                "sentence": q_loc["sentence"],
                "char_blocks": blocks,
            })
    return segments


def _assign_dimension(segment_text: str) -> str:
    """根据片段内容归属文本维度。"""
    sents = _split_sents(segment_text)
    avg_len = sum(len(s) for s in sents) / len(sents) if sents else 99
    if len(sents) >= 3 and avg_len <= 8:  # 短句排比 / 意象句 → 行文习惯
        return "行文习惯"
    if any(w in segment_text for w in PLOT_WORDS):
        return "故事剧情"
    if any(w in segment_text for w in CHARACTER_WORDS):
        return "人物设定"
    return "专属名词"


def _severity(segment: dict, dimension: str) -> dict:
    """三级关注：重点关注（深红）/ 一般关注（中蓝）/ 辅助观察（浅绿）。"""
    length = segment["length"]
    if dimension == "行文习惯":
        return {"level": "辅助观察", "color": "green", "code": "low"}
    if dimension in ("故事剧情", "人物设定") and length >= 12:
        return {"level": "重点关注", "color": "red", "code": "high"}
    if length >= 8:
        return {"level": "一般关注", "color": "blue", "code": "mid"}
    return {"level": "辅助观察", "color": "green", "code": "low"}


def compare_texts(query_text: str, ref_text: str, q_feat: dict, r_feat: dict,
                  idf: dict[str, float]) -> dict:
    """
    比对待测稿与单篇底库稿件，输出相似度、维度分、高亮索引与初步标签。
    """
    # ---- 字面 / 向量相似度 ----
    bigram_jac = jaccard(q_feat["bigram_set"], r_feat["bigram_set"])
    tfidf_cos = cosine(q_feat.get("tfidf", {}), r_feat.get("tfidf", {}))
    segments = find_common_segments(query_text, ref_text, min_len=6)
    matched_chars = sum(s["length"] for s in segments)
    coverage = matched_chars / (q_feat["char_count"] or 1)

    overall = 100 * (0.45 * bigram_jac + 0.35 * tfidf_cos + 0.20 * coverage)
    overall = round(_clamp(overall), 1)

    # ---- 四维度评分 ----
    q_style, r_style = q_feat["style"], r_feat["style"]
    len_diff = abs(q_style["avg_sentence_len"] - r_style["avg_sentence_len"])
    short_diff = abs(q_style["short_sentence_ratio"] - r_style["short_sentence_ratio"])
    punct_diff = abs(q_style["punctuation_ratio"] - r_style["punctuation_ratio"])
    style_close = _clamp(100 - 25 * len_diff - 40 * short_diff - 200 * punct_diff)
    style_score = round(_clamp(0.5 * style_close + 50 * bigram_jac), 1)

    plot_kw = sum(1 for w in PLOT_WORDS if w in query_text and w in ref_text) / len(PLOT_WORDS)
    plot_score = round(_clamp(100 * (0.6 * coverage + 0.4 * plot_kw)), 1)

    char_q = {t for t in q_feat["tokens"] if any(w in t for w in CHARACTER_WORDS)}
    char_r = {t for t in r_feat["tokens"] if any(w in t for w in CHARACTER_WORDS)}
    char_score = round(_clamp(100 * (0.6 * jaccard(char_q, char_r) + 0.4 * plot_kw)), 1)

    rare_q = {t for t in q_feat["tokens"] if idf.get(t, 1.0) >= 1.2}
    rare_r = {t for t in r_feat["tokens"] if idf.get(t, 1.0) >= 1.2}
    noun_score = round(_clamp(100 * jaccard(rare_q, rare_r)), 1)

    dimensions = [
        {"key": "writing_style", "name": "行文习惯", "weight": 0.35, "score": style_score},
        {"key": "plot", "name": "故事剧情", "weight": 0.30, "score": plot_score},
        {"key": "character", "name": "人物设定", "weight": 0.20, "score": char_score},
        {"key": "proper_noun", "name": "专属名词", "weight": 0.15, "score": noun_score},
    ]

    # ---- 高亮索引（段落 / 句子定位 + 字符偏移） ----
    highlights = []
    for idx, seg in enumerate(segments, start=1):
        dimension = _assign_dimension(seg["paragraph"])
        sev = _severity(seg, dimension)
        highlights.append({
            "highlight_id": f"H{idx:02d}",
            "dimension": dimension,
            "severity": sev["level"],
            "severity_code": sev["code"],
            "severity_color": sev["color"],
            "text": seg["text"],
            "query_start": seg["query_start"],
            "query_end": seg["query_end"],
            "ref_start": seg["ref_start"],
            "ref_end": seg["ref_end"],
            "ref_source": "base_01_灯塔守夜人.txt",
            "location": {
                "paragraph_index": seg["paragraph_index"],
                "sentence_index": seg["sentence_index"],
                "offset_in_paragraph": seg["query_start"] - next(
                    s["start"] for s in _sentence_locations(query_text)
                    if s["paragraph_index"] == seg["paragraph_index"]
                ),
            },
            "length": seg["length"],
        })

    # ---- 初步分析标签（阈值规则，第3周接入统一规则引擎） ----
    labels = []
    if overall >= 75:
        labels.append({"code": "suspected_plagiarism", "name": "疑似洗稿", "level": "red",
                       "reason": f"加权相似度 {overall}，处于红区（75–100）"})
    elif overall >= 40:
        labels.append({"code": "needs_review", "name": "需人工复核", "level": "amber",
                       "reason": f"加权相似度 {overall}，处于黄区（40–74）"})
    else:
        labels.append({"code": "low_risk", "name": "低风险", "level": "green",
                       "reason": f"加权相似度 {overall}，处于绿区（0–39）"})

    if any(h["length"] >= 15 for h in highlights):
        labels.append({"code": "paragraph_copy", "name": "段落级复制", "level": "red",
                       "reason": "检出 15 字以上整段重合片段"})
    if style_score >= 80:
        labels.append({"code": "style_close", "name": "行文风格接近", "level": "amber",
                       "reason": "句长分布、短句节奏与参考稿高度接近"})
    if noun_score >= 60:
        labels.append({"code": "noun_overlap", "name": "专有名词重合", "level": "amber",
                       "reason": "高 IDF 专属名词集合重合度较高"})

    # 结尾立意差异（正向贡献点，反向支持独立性）
    paras_q = _split_paragraphs(query_text)
    paras_r = _split_paragraphs(ref_text)
    if paras_q and paras_r and paras_q[-1] != paras_r[-1]:
        labels.append({"code": "original_ending", "name": "原创立意差异", "level": "green",
                       "reason": "结尾段落与参考稿不同，属原创贡献点，不计入风险"})

    return {
        "overall_similarity": overall,
        "bigram_jaccard": round(bigram_jac, 4),
        "tfidf_cosine": round(tfidf_cos, 4),
        "lcs_coverage": round(coverage, 4),
        "dimensions": dimensions,
        "highlights": highlights,
        "labels": labels,
        "matched_segment_count": len(highlights),
    }
