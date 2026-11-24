# -*- coding: utf-8 -*-
"""
文本特征提取模块（成员A · 第1周）
----------------------------------
职责：
  1. 段落 / 句子切分；
  2. 中文分词（jieba，不可用时回退到字二元组）；
  3. 字二元组（char bigram）集合；
  4. TF-IDF 词袋向量；
  5. 行文风格统计（句长、标点占比、短句比例）。

说明：本模块只做特征抽取，不做相似度判定，比对逻辑见 similarity.py。
"""

import re
import math
from collections import Counter

try:
    import jieba
    jieba.setLogLevel(60)  # 关闭 jieba 初始化日志
    _HAS_JIEBA = True
except ImportError:  # 兜底：未装 jieba 时使用字 bigram
    _HAS_JIEBA = False

# 常用中文停用词（演示底库规模较小，覆盖常见功能词即可）
STOPWORDS = set(
    "的 了 和 是 在 他 她 它 我 你 也 都 就 还 而 但 与 及 上 下 里 中 "
    "把 被 让 向 从 对 这 那 一 个 着 过 地 得 吗 呢 吧 啊 么 之 其 "
    "没有 已经 可以 因为 所以 但是 然后 最后 之后 之前"
    .split()
)

_SENT_RE = re.compile(r"(?<=[。！？!?；;])")
_PARA_RE = re.compile(r"\n\s*\n")
_PUNCT_RE = re.compile(r"[，。！？；：、“”‘’（）《》—…\s,.!?;:()\"'\-]")


def clean_text(text: str) -> str:
    """规整空白字符，保留原始换行结构。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    """按空行切分段落，过滤空段。"""
    return [p.strip() for p in _PARA_RE.split(text) if p.strip()]


def split_sentences(paragraph: str) -> list[str]:
    """按句末标点切分句子，保留标点。"""
    parts = [s.strip() for s in _SENT_RE.split(paragraph) if s.strip()]
    return parts


def tokenize(text: str) -> list[str]:
    """中文分词；过滤停用词与纯标点。"""
    if _HAS_JIEBA:
        words = [w.strip() for w in jieba.lcut(text) if w.strip()]
    else:
        words = list(re.sub(r"\s+", "", text))
    return [w for w in words if w not in STOPWORDS and not _PUNCT_RE.fullmatch(w)]


def char_bigrams(text: str) -> list[str]:
    """字二元组，用于短文本 / 仿写场景的字面重合度计算。"""
    chars = re.sub(r"\s+", "", _PUNCT_RE.sub("", text))
    if len(chars) < 2:
        return []
    return [chars[i : i + 2] for i in range(len(chars) - 1)]


def _term_freq(tokens: list[str]) -> dict[str, float]:
    tf = Counter(tokens)
    total = sum(tf.values()) or 1
    return {k: v / total for k, v in tf.items()}


def build_idf(docs_tokens: list[list[str]]) -> dict[str, float]:
    """根据底库语料构建 IDF 表。"""
    n = len(docs_tokens) or 1
    df = Counter()
    for tokens in docs_tokens:
        for t in set(tokens):
            df[t] += 1
    return {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}


def tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = _term_freq(tokens)
    return {t: round(f * idf.get(t, 1.0), 6) for t, f in tf.items()}


def style_stats(text: str) -> dict:
    """行文风格统计：平均句长、短句占比、标点占比。"""
    paras = split_paragraphs(text)
    sentences = [s for p in paras for s in split_sentences(p)]
    lengths = [len(re.sub(r"\s+", "", s)) for s in sentences]
    avg_len = sum(lengths) / len(lengths) if lengths else 0.0
    short_ratio = sum(1 for l in lengths if l <= 8) / len(lengths) if lengths else 0.0
    punct_ratio = len(_PUNCT_RE.findall(text)) / (len(text) or 1)
    return {
        "paragraph_count": len(paras),
        "sentence_count": len(sentences),
        "avg_sentence_len": round(avg_len, 2),
        "short_sentence_ratio": round(short_ratio, 3),
        "punctuation_ratio": round(punct_ratio, 3),
    }


def extract_text_features(text: str, idf: dict[str, float] | None = None) -> dict:
    """抽取单篇文本的完整特征，返回可序列化的字典。"""
    text = clean_text(text)
    tokens = tokenize(text)
    bigrams = char_bigrams(text)
    features = {
        "char_count": len(re.sub(r"\s+", "", text)),
        "tokens": tokens,
        "bigrams": bigrams,
        "token_set": sorted(set(tokens)),
        "bigram_set": sorted(set(bigrams)),
        "style": style_stats(text),
    }
    if idf is not None:
        features["tfidf"] = tfidf_vector(tokens, idf)
    return features
