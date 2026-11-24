# 成员A · 第1周交付物（文本 / 音频算法 + 文本前端组件）

> 项目：AIGC 内容版权比对与合规预检系统
> 角色：成员A（文本/音频算法 + 文本前端组件）
> 周次：第1周 —— 接口定义后全面并行：后端文本/音频提取、首批底库入库、文本高亮前端组件

---

## 一、交付清单（对照任务大纲）

| 大纲要求 | 交付文件 | 说明 |
| --- | --- | --- |
| 后端 · 文本特征提取 | `backend/text_features.py` | 段落/句子切分、jieba 分词、字二元组、TF-IDF 向量、行文风格统计 |
| 后端 · 音频指纹提取 | `backend/audio_fingerprint.py` | WAV 读取、16 步节奏包络、主导频段 + 能量档位指纹、CRC32 哈希 |
| 后端 · 文本相似度比对 | `backend/similarity.py` | TF-IDF 余弦、二元组 Jaccard、句段对齐 LCS 公共片段、四维度评分、标签规则 |
| 后端 · 音频相似度比对 | `backend/audio_fingerprint.py` | 指纹步长 ±1 容差命中比 + 哈希 Jaccard，输出音频相似度 |
| 首批底库数据整理并入库 | `data/base_text/`、`data/base_audio/`、`output/base_index.json` | 3 篇底库文本 + 3 段演示音频入库；索引含特征、指纹与 IDF 表；预留 FAISS 接入位 |
| 前端 · 文本高亮渲染组件 | `frontend/text_highlight_component.html` | 按字符偏移渲染三级高亮，编号徽章、段落/句子定位、维度与来源明细 |
| 前端 · 雷达图文本维度组件 | `frontend/radar_text_component.html` | 菱形四维雷达 + 权重条 + 关键指标，数据读自后端产出 |
| 交付 · 带高亮索引的真实 JSON | `output/text_analysis.json` | 每处高亮含 `query_start/query_end`、段落/句子下标、底库偏移与来源文件 |
| 交付 · 分析标签 | `output/text_analysis.json` → `labels` | 需人工复核 / 段落级复制 / 专有名词重合 / 原创立意差异（疑似洗稿等红区标签按阈值触发） |
| 交付 · 音频比对结果 JSON | `output/audio_analysis.json` | 待测录音变体 vs 底库指纹排序、命中步数、音频相似度与初步标签 |
| 交付 · 前端组件截图 | `screenshots/01_文本高亮组件.png`、`screenshots/02_文本维度雷达图组件.png` | Edge 无头模式截取，与离线 HTML 同口径 |

---

## 二、目录结构

```
成员A_第1周交付物/
├── backend/
│   ├── text_features.py        # 文本特征提取
│   ├── audio_fingerprint.py    # 音频指纹提取与比对
│   ├── similarity.py             # 文本相似度 / 维度评分 / 高亮索引 / 标签规则
│   ├── ingest_base.py           # 底库入库、本地检索（FAISS 钩子预留）
│   └── run_pipeline.py          # 一键流水线：入库 → 比对 → 产出 JSON → 注入前端数据
├── data/
│   ├── base_text/               # 首批底库文本（3 篇）
│   ├── base_audio/              # 首批底库演示音频（3 段，程序生成）
│   └── query/                   # 待测稿文本 + 待测音频变体
├── output/
│   ├── base_index.json          # 底库索引（文本特征 + 音频指纹 + IDF）
│   ├── text_analysis.json       # 文本比对结果（高亮索引 / 维度分 / 标签）
│   └── audio_analysis.json      # 音频指纹比对结果
├── frontend/
│   ├── index.html               # 两个组件的预览入口
│   ├── text_highlight_component.html
│   ├── radar_text_component.html
│   └── component_data.js        # 流水线自动生成，供离线 HTML 读取
├── screenshots/                 # 前端组件截图
├── requirements.txt
├── 运行流水线.bat
└── README.md
```

## 三、运行方式

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行流水线（入库 + 比对 + 刷新前端数据）
cd backend
python run_pipeline.py
```

- 文本前端组件：双击 `frontend/index.html` 或对应组件 HTML（file:// 离线可开）。
- 重新截图：Edge 无头模式
  `msedge --headless=new --screenshot=输出.png --window-size=1280,1500 file:///...html`

## 四、本次演示样本结果（真实算法产出）

| 项目 | 结果 |
| --- | --- |
| 待测稿 | `query_雾港来信_生成稿.txt` |
| 命中底库 | `base_01_灯塔守夜人.txt`（检索分 0.7328，显著高于其余两篇） |
| 综合相似度 | 69.6 / 100（黄区 · 需人工复核） |
| 维度分 | 行文习惯 66.7 ｜ 故事剧情 73.0 ｜ 人物设定 92.0 ｜ 专属名词 74.5 |
| 高亮片段 | 5 处：重点关注 4（剧情 3 + 人设 1），辅助观察 1（行文修辞） |
| 文本标签 | 需人工复核、段落级复制、专有名词重合、原创立意差异（正向） |
| 音频比对 | 变体命中 `audio_01_海风云.wav`，相似度 70.5，标签「疑似音频复用」 |

## 五、`text_analysis.json` 关键字段

```jsonc
{
  "overall_similarity": 69.6,          // 综合相似度 0–100
  "risk_band": { "code": "amber", "name": "需复核", "range": "40–74" },
  "dimensions": [                       // 雷达图四维，含权重
    { "key": "plot", "name": "故事剧情", "weight": 0.30, "score": 73.0 }
  ],
  "highlights": [                      // 带高亮索引的片段
    {
      "highlight_id": "H01",
      "dimension": "故事剧情",
      "severity": "重点关注", "severity_code": "high",
      "text": "十一月的海风吹过长堤……",
      "query_start": 21, "query_end": 43,        // 待测稿字符偏移
      "ref_start": 32,  "ref_end": 54,            // 底库稿字符偏移
      "ref_source": "base_01_灯塔守夜人.txt",
      "location": { "paragraph_index": 2, "sentence_index": 1, "offset_in_paragraph": 0 }
    }
  ],
  "labels": [ { "code": "paragraph_copy", "name": "段落级复制", "level": "red", "reason": "…" } ]
}
```

## 六、与其他成员的接口预留

- **对成员C（系统架构 / 业务引擎）**
  - 检索接口：`ingest_base.search_texts / search_audios` 当前为本地 brute-force，`base_index.json` 内 `faiss_hook` 已标注待接入 FAISS 向量索引；替换底层实现后上层流水线不变。
  - 标签字段：`labels[].code / name / level / reason` 已结构化，第3周交由成员C的规则引擎做「标签 → 处置建议」转换。
  - 报告消费：`dimensions` 供雷达图组件，`highlights` 供功能二研判工作台画框/高亮，`risk_band` 供红绿灯看板。
- **对成员B（视觉/视频算法）**：本包文本侧偏移字段为字符级；B 侧图片框坐标、视频时间戳字段在其交付包内对齐同一套 `highlights` 结构（`location` 按模态替换为 `bbox` / `time_range`）。

## 七、边界与后续周次衔接

1. 第1周为算法原型：文本分词/相似度基于 jieba + TF-IDF + 字二元组 + 公共片段；音频指纹为节奏包络原型，第2–3周再细化声纹、原声台词维度。
2. 演示音频由脚本生成（`generate_demo_wav`），仅用于入库与流程联调，正式演示替换为真实素材。
3. 标签阈值为成员A侧初步规则；最终标签体系与「标签转建议」规则引擎由成员C在第3周统一收口。
4. 所有相似度、标签均为技术比对提示，不构成侵权或不侵权的法律认定。
