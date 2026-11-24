// 由 run_pipeline.py 自动生成，请勿手改；重新运行流水线即可刷新
window.ANALYSIS_DATA = {
  "report_id": "AIGC-2026-W1-A-185623",
  "query_file": "query_雾港来信_生成稿.txt",
  "best_match": {
    "item_id": "T001",
    "file": "base_01_灯塔守夜人.txt",
    "title": "灯塔守夜人（底库参考稿 · 2024-09 · 海边文学社）",
    "retrieval_score": 0.7328,
    "tfidf_cosine": 0.814,
    "bigram_jaccard": 0.6111
  },
  "overall_similarity": 69.6,
  "risk_band": {
    "code": "amber",
    "name": "需复核",
    "range": "40–74"
  },
  "dimensions": [
    {
      "key": "writing_style",
      "name": "行文习惯",
      "weight": 0.35,
      "score": 66.7
    },
    {
      "key": "plot",
      "name": "故事剧情",
      "weight": 0.3,
      "score": 73.0
    },
    {
      "key": "character",
      "name": "人物设定",
      "weight": 0.2,
      "score": 92.0
    },
    {
      "key": "proper_noun",
      "name": "专属名词",
      "weight": 0.15,
      "score": 74.5
    }
  ],
  "highlights": [
    {
      "highlight_id": "H01",
      "dimension": "故事剧情",
      "severity": "重点关注",
      "severity_code": "high",
      "severity_color": "red",
      "text": "十一月的海风吹过长堤，港口安静得只剩下潮水。",
      "query_start": 21,
      "query_end": 43,
      "ref_start": 32,
      "ref_end": 54,
      "ref_source": "base_01_灯塔守夜人.txt",
      "location": {
        "paragraph_index": 2,
        "sentence_index": 1,
        "offset_in_paragraph": 0
      },
      "length": 22
    },
    {
      "highlight_id": "H02",
      "dimension": "故事剧情",
      "severity": "重点关注",
      "severity_code": "high",
      "severity_color": "red",
      "text": "轮渡停航的第三天，他收到一封没有署名的信。",
      "query_start": 45,
      "query_end": 66,
      "ref_start": 56,
      "ref_end": 77,
      "ref_source": "base_01_灯塔守夜人.txt",
      "location": {
        "paragraph_index": 3,
        "sentence_index": 1,
        "offset_in_paragraph": 0
      },
      "length": 21
    },
    {
      "highlight_id": "H03",
      "dimension": "故事剧情",
      "severity": "重点关注",
      "severity_code": "high",
      "severity_color": "red",
      "text": "循着信中的坐标，他在废弃码头找到了旧航标。",
      "query_start": 66,
      "query_end": 87,
      "ref_start": 77,
      "ref_end": 98,
      "ref_source": "base_01_灯塔守夜人.txt",
      "location": {
        "paragraph_index": 3,
        "sentence_index": 2,
        "offset_in_paragraph": 21
      },
      "length": 21
    },
    {
      "highlight_id": "H04",
      "dimension": "人物设定",
      "severity": "重点关注",
      "severity_code": "high",
      "severity_color": "red",
      "text": "守塔人早已失去听力，只能用灯光回应海上的呼唤。",
      "query_start": 89,
      "query_end": 112,
      "ref_start": 100,
      "ref_end": 123,
      "ref_source": "base_01_灯塔守夜人.txt",
      "location": {
        "paragraph_index": 4,
        "sentence_index": 1,
        "offset_in_paragraph": 0
      },
      "length": 23
    },
    {
      "highlight_id": "H05",
      "dimension": "行文习惯",
      "severity": "辅助观察",
      "severity_code": "low",
      "severity_color": "green",
      "text": "海面像一封尚未拆开的信。",
      "query_start": 122,
      "query_end": 134,
      "ref_start": 133,
      "ref_end": 145,
      "ref_source": "base_01_灯塔守夜人.txt",
      "location": {
        "paragraph_index": 5,
        "sentence_index": 3,
        "offset_in_paragraph": 8
      },
      "length": 12
    }
  ],
  "labels": [
    {
      "code": "needs_review",
      "name": "需人工复核",
      "level": "amber",
      "reason": "加权相似度 69.6，处于黄区（40–74）"
    },
    {
      "code": "paragraph_copy",
      "name": "段落级复制",
      "level": "red",
      "reason": "检出 15 字以上整段重合片段"
    },
    {
      "code": "noun_overlap",
      "name": "专有名词重合",
      "level": "amber",
      "reason": "高 IDF 专属名词集合重合度较高"
    },
    {
      "code": "original_ending",
      "name": "原创立意差异",
      "level": "green",
      "reason": "结尾段落与参考稿不同，属原创贡献点，不计入风险"
    }
  ],
  "severity_summary": {
    "high": 4,
    "mid": 0,
    "low": 1
  },
  "paragraphs": [
    "雾港来信（待测稿 · 2026-11）",
    "十一月的海风吹过长堤，港口安静得只剩下潮水。",
    "轮渡停航的第三天，他收到一封没有署名的信。循着信中的坐标，他在废弃码头找到了旧航标。",
    "守塔人早已失去听力，只能用灯光回应海上的呼唤。",
    "潮来了。灯亮了。海面像一封尚未拆开的信。",
    "他终于放下旧日的歉意，决定为自己写下回信。"
  ]
};
