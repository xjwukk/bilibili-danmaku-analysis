# 应用层模块 — 运行与测试文档

> **学生B（应用层）**：负责 `nlp_processing`（NLP 处理：分词/情感/LDA/关键词/NER 等）与 `web_frontend`（ECharts 前端可视化）两大模块的运行与测试。
>
> 本文档为**实操 runbook**，逐步指导如何在本地完成 NLP 处理流水线与前端可视化页面的端到端验证。

---

## 目录

1. [环境准备](#1-环境准备)
2. [模块与文件清单](#2-模块与文件清单)
3. [功能 1：弹幕分词（jieba / pkuseg）](#3-功能-1弹幕分词jieba--pkuseg)
4. [功能 2：词频统计 + 词云数据](#4-功能-2词频统计--词云数据)
5. [功能 3：情感分析（基础版）](#5-功能-3情感分析基础版)
6. [功能 4：增强情感分析（否定/程度/表情/转折）](#6-功能-4增强情感分析否定程度表情转折)
7. [功能 5：NER 实体识别](#7-功能-5ner-实体识别)
8. [功能 6：关键词抽取（TF-IDF + TextRank）](#8-功能-6关键词抽取tf-idf--textrank)
9. [功能 7：LDA 主题建模（coherence 寻优）](#9-功能-7lda-主题建模coherence-寻优)
10. [功能 8：情感分离 LDA](#10-功能-8情感分离-lda)
11. [功能 9：增强分析（情感趋势/类型/时间/用户/共现）](#11-功能-9增强分析情感趋势类型时间用户共现)
12. [功能 10：前端可视化（ECharts 词云 + 图表）](#12-功能-10前端可视化echarts-词云--图表)
13. [端到端联调测试](#13-端到端联调测试)
14. [常见问题排查](#14-常见问题排查)

---

## 1. 环境准备

### 1.1 操作系统

Windows 10/11、macOS、Linux 均可；案例项目在 Windows 11 下验证。

### 1.2 Python 版本

**Python 3.7+**（推荐 3.8/3.9，已验证）。

```bash
python --version
```

### 1.3 全部依赖

```bash
pip install jieba pkuseg snownlp gensim wordcloud cnsenti scikit-learn numpy pandas matplotlib Pillow
```

> **注意**：
> - `pkuseg` 首次使用会下载约 200 MB 模型，若网络受限可跳过（脚本有 jieba 降级）
> - `snowlp` 训练数据 `online_shopping_10_cats.csv` 已包含在 `nlp_processing/`，无需额外下载
> - `sentiment_model.marshal.3` 是训练好的 SnowNLP 模型，可直接使用

### 1.4 前置：学生A 清洗后的数据

应用层所有模块的输入是 `nlp_processing/cleaned_danmaku.json`，由学生A产出。若该文件不存在：

```bash
# 1. 跑学生A的爬虫
cd "F:\Claude Project\大数据应用系统开发实践\bilibili_crawler"
python bilibili_crawler_v3.py

# 2. 跑学生A的清洗
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python clean_danmaku.py
```

确认 `cleaned_danmaku.json` 存在后再开始应用层流程。

### 1.5 前端：仅需任意静态 HTTP 服务器

```bash
# Python 自带（推荐）
python -m http.server 8080

# 或 Node.js
npx http-server -p 8080
```

---

## 2. 模块与文件清单

| 文件 | 作用 | 输入 | 输出 |
|------|------|------|------|
| `nlp_processing/segmentation.py` | pkuseg / jieba 分词 + 词性 | cleaned_danmaku.json | 分词结果 |
| `nlp_processing/nlp_process.py` | 词频统计 + 词云数据 + 基础 LDA | cleaned_danmaku.json | wordfreq.json, lda_topics.json |
| `nlp_processing/generate_wordcloud_v2.py` | 生成 ECharts 词云 JSON | wordfreq.json | 词云前端数据 |
| `nlp_processing/sentiment_lexicon.py` | SnowNLP 情感打分 | cleaned_danmaku.json | sentiment.json |
| `nlp_processing/sentiment_enhanced.py` | 增强版情感（规则+否定+表情） | cleaned_danmaku.json | 增强情感结果 |
| `nlp_processing/ner_recognition.py` | 命名实体识别（人名/地名/机构/技术词） | cleaned_danmaku.json | ner_entities.json |
| `nlp_processing/keyword_extraction.py` | TF-IDF + TextRank 关键词 | cleaned_danmaku.json | keywords.json |
| `nlp_processing/lda_sentiment_topics.py` | 情感分离 LDA（积极/消极分别建模） | cleaned_danmaku.json | lda_sentiment_topics.json |
| `nlp_processing/sentiment_trend.py` | 情感趋势（时间序列） | cleaned_danmaku.json + sentiment.json | sentiment_trend.json |
| `nlp_processing/danmaku_classifier.py` | 弹幕类型分类（祝福/玩梗/刷屏/提问） | cleaned_danmaku.json | danmaku_classified.json |
| `nlp_processing/danmaku_time_distribution.py` | 弹幕时间分布 | cleaned_danmaku.json | danmaku_time_distribution.json |
| `nlp_processing/user_behavior_analysis.py` | 用户行为分析 | cleaned_danmaku.json | user_behavior.json |
| `nlp_processing/word_cooccurrence.py` | 词语共现网络 | cleaned_danmaku.json | word_cooccurrence.json |
| `nlp_processing/sentiment_distribution.py` | 情感分布可视化（生成 PNG） | sentiment.json | sentiment_distribution.png |
| `web_frontend/index.html` | 词云展示页 + 时间轴 | wordfreq.json + time_dist.json | 浏览器页面 |
| `web_frontend/charts.html` | 统计图表页（情感/趋势/类型/用户） | 多个 json | 浏览器页面 |
| `web_frontend/js/data.js` | DataService 统一数据加载 | - | - |
| `web_frontend/js/wordcloud.js` | ECharts 词云组件 | - | - |
| `web_frontend/js/charts.js` | 统计图表组件 | - | - |
| `web_frontend/js/timeline.js` | 时间轴组件 | - | - |

---

## 3. 功能 1：弹幕分词（jieba / pkuseg）

### 3.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python segmentation.py
```

### 3.2 预期输出

```
============================================================
分词模块 - pkuseg 升级版
============================================================
加载 pkuseg 模型...
分词进度: 1000/3515
分词进度: 2000/3515
分词进度: 3000/3515
完成！

分词统计:
  输入弹幕: 3515 条
  总词数:   11623
  不重复词: 4105

Top 20 高频词:
  AI      142
  权限     87
  模型     76
  token   65
  ...
```

### 3.3 产物

- **生成**：`nlp_processing/wordfreq_pkuseg.json`（pkuseg 版词频，可与 jieba 版对比）

### 3.4 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| pkuseg 加载 | 模型成功 | 无异常 |
| 分词总词数 | 10000~13000 | 数量在 [10000, 13000] |
| 不重复词数 | 3000~5000 | 数量在 [3000, 5000] |
| Top 词 | "AI" 排名前 5 | `wordfreq_pkuseg.json[0]['word']` 含 "AI" |

### 3.5 自检

```bash
python -c "
import json
d = json.load(open('nlp_processing/wordfreq_pkuseg.json', encoding='utf-8'))
print('Top 5:', [w['word'] for w in d['top_100'][:5]])
print('Total:', d['total_words'], 'Unique:', d['unique_words'])
"
```

---

## 4. 功能 2：词频统计 + 词云数据

### 4.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"

# 1. 基础词频 + LDA
python nlp_process.py

# 2. 词云生成（ECharts 格式）
python generate_wordcloud_v2.py
```

### 4.2 预期输出（nlp_process.py）

```
============================================================
NLP 处理模块
============================================================
加载停用词: 743 个
读取清洗后弹幕: 3515 条

[1/3] 分词 + 停用词过滤
  完成，总词数: 11623

[2/3] 词频统计
  Top 20: AI(142), 权限(87), 模型(76), token(65)...

[3/3] LDA 主题建模
  寻找最优主题数 (3-8)...
  最优: 8 个主题, coherence=0.6135

输出:
  wordfreq.json       (Top 100)
  lda_topics.json     (8 主题)
```

### 4.3 预期输出（generate_wordcloud_v2.py）

```
Loading word frequency data...
Top words: 100
Generating wordcloud data...
Saved: web_frontend/data/wordcloud.json
✓ 完成
```

### 4.4 产物

| 文件 | 内容 |
|------|------|
| `nlp_processing/wordfreq.json` | Top 100 词频 |
| `nlp_processing/lda_topics.json` | 8 主题及关键词 |
| `web_frontend/data/wordcloud.json` | ECharts 词云数据 |

### 4.5 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 词频输出 | Top 100 | `len(wordfreq['top_100']) == 100` |
| 排序正确 | 按 freq 降序 | `freq[i] >= freq[i+1]` |
| 词云数据 | 含 name/value 字段 | 字段齐全 |
| LDA 主题 | 8 主题 | `len(lda_topics['topics']) == 8` |
| coherence | > 0.5 | `lda_topics['coherence'] > 0.5` |

---

## 5. 功能 3：情感分析（基础版）

### 5.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python sentiment_lexicon.py
```

### 5.2 预期输出

```
============================================================
情感分析 - SnowNLP + HowNet 词典
============================================================
加载词典: 20000+ 词
加载 SnowNLP 模型...
分析 3515 条弹幕...
进度: 1000/3515
...

情感分布:
  正面:  266 条  (7.57%)
  负面:   77 条  (2.19%)
  中性: 3172 条  (90.24%)

保存: sentiment.json
保存: positive_danmakus.json  (266 条)
保存: negative_danmakus.json  (77 条)
```

### 5.3 产物

| 文件 | 内容 |
|------|------|
| `nlp_processing/sentiment.json` | 整体统计 + 每条弹幕得分 |
| `nlp_processing/positive_danmakus.json` | 正面弹幕列表 |
| `nlp_processing/negative_danmakus.json` | 负面弹幕列表 |

### 5.4 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 分析完成 | 3515 条全部打分 | 无报错 |
| 三类比例和 | 100% | `pos+neg+neu == total` |
| 正面 < 50% | 该视频以中性/技术向弹幕为主 | pos < 50% |
| 极端值 | 负面应有 50~150 条 | 数量在 [50, 150] |

### 5.5 自检

```bash
python -c "
import json
d = json.load(open('nlp_processing/sentiment.json', encoding='utf-8'))
s = d['stats']
print(f\"Total: {s['total']}, +: {s['positive']['count']}, -: {s['negative']['count']}, =: {s['neutral']['count']}\")
"
```

---

## 6. 功能 4：增强情感分析（否定/程度/表情/转折）

### 6.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python sentiment_enhanced.py
```

### 6.2 预期输出

```
============================================================
增强版情感分析
============================================================
规则集:
  否定词: 9 个
  程度副词: 7 个
  表情符号: 6 个
  转折检测: 4 种句式

分析中...
完成 3515 条

对比基础版:
                基础版    增强版
  正面          42.30%    42.12%
  负面          39.94%    32.47%
  中性          17.75%    25.41%

增强效果:
  负面 ↓ 7.47%（部分误判被修正为中性）
  中性 ↑ 7.66%

保存: sentiment_enhanced.json
```

### 6.3 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 规则加载 | 4 类规则 | 输出含 "规则集" 列表 |
| 增强对比 | 负面比例下降 | `enhanced['negative'] < basic['negative']` |
| JSON 完整 | 含 stats + details | 字段齐全 |

### 6.4 自检样例

```python
# 单元测试片段
from sentiment_enhanced import EnhancedSentimentAnalyzer
ana = EnhancedSentimentAnalyzer()
assert ana.analyze("这个视频太棒了")['label'] == 'positive'
assert ana.analyze("垃圾视频")['label'] == 'negative'
assert ana.analyze("一般般吧")['label'] == 'neutral'
print("✓ 增强情感分析单元测试通过")
```

---

## 7. 功能 5：NER 实体识别

### 7.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python ner_recognition.py
```

### 7.2 预期输出

```
============================================================
NER 实体识别 - 基于词性标注
============================================================
分析 3515 条弹幕...

实体统计:
  人名(nr):  234 次 / 45 个唯一
  地名(ns):  123 次 / 28 个唯一
  机构(nt):   45 次 / 12 个唯一
  专名(nz):  567 次 / 89 个唯一
  技术词:    312 次 / 56 个唯一

Top 10 实体:
  OpenClaw: 87
  ChatGPT:  54
  豆包:     42
  蔡徐坤:   23
  ...

保存: ner_entities.json
```

### 7.3 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 实体总数 | 各类合计 800+ | 数量 > 500 |
| 技术词 | 出现 OpenClaw / AI | 列表中含 "OpenClaw" |
| Top 排序 | 频次降序 | 排序正确 |

---

## 8. 功能 6：关键词抽取（TF-IDF + TextRank）

### 8.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python keyword_extraction.py
```

### 8.2 预期输出

```
============================================================
关键词抽取 - TF-IDF + TextRank 融合
============================================================
[1/2] TF-IDF
  Top 10: AI(0.023), 权限(0.020), 模型(0.019), token(0.018)...

[2/2] TextRank
  Top 10: AI(1.234), 权限(0.987), 模型(0.956), token(0.912)...

[融合] 综合得分
  1. AI       0.854
  2. 权限     0.723
  3. 模型     0.698
  4. token    0.671
  5. 工具     0.589
  ...

保存: keywords.json
```

### 8.3 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| TF-IDF 输出 | 10+ 关键词 | 数量 ≥ 10 |
| TextRank 输出 | 10+ 关键词 | 数量 ≥ 10 |
| 融合结果 | 含综合得分 | `score` 字段存在 |
| Top 1 | "AI" | 综合得分第 1 为 "AI" |

---

## 9. 功能 7：LDA 主题建模（coherence 寻优）

### 9.1 一键运行

LDA 已集成在 `nlp_process.py`，参考 [§4.1](#41-一键运行)。

若需单独运行：

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python -c "
from nlp_process import lda_topic_modeling
import json
danmaku = json.load(open('cleaned_danmaku.json', encoding='utf-8'))['danmaku_list']
lda, _, _ = lda_topic_modeling(danmaku, num_topics=8)
for i, topic in lda.print_topics(num_words=5):
    print(f'主题 {i}: {topic}')
"
```

### 9.2 预期输出

```
主题 0: AI 模型 人类 智能 学习
主题 1: 权限 安全 cookie 浏览器 数据
主题 2: 视频 讲解 老师 概念 通俗
...
coherence=0.6135
```

### 9.3 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 主题数 | 8 | `num_topics == 8` |
| coherence | > 0.5 | `lda_topics.json['coherence'] > 0.5` |
| 关键词 | 5 个/主题 | 每个主题含 5 个词 |

---

## 10. 功能 8：情感分离 LDA

### 10.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"
python lda_sentiment_topics.py
```

### 10.2 预期输出

```
============================================================
情感分离 LDA - 积极/消极分别建模
============================================================
积极弹幕: 266 条 (SnowNLP > 0.7)
消极弹幕:  77 条 (SnowNLP < 0.3)

积极 4 主题:
  主题1: 人类 模型 能力 解决 公司
  主题2: 进化 可爱 奶茶 记忆 时代
  主题3: 权限 老师 工具 任务 创造
  主题4: 学习 豆包 世界 手机 危机

消极 4 主题:
  主题1: 不行 炒作 风险 算力 链接
  主题2: 问题 不会 吓人 审核 污染
  主题3: 电脑 软件 权限 消耗 手机
  主题4: 安全 赚钱 觉醒 整合 系统

保存: lda_sentiment_topics.json
```

### 10.3 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 积极主题数 | 4 | `len(positive_topics) == 4` |
| 消极主题数 | 4 | `len(negative_topics) == 4` |
| 关键词质量 | 主题内聚 | 关键词相关（如"安全/风险"） |

---

## 11. 功能 9：增强分析（情感趋势/类型/时间/用户/共现）

### 11.1 完整流水线

```bash
cd "F:\Claude Project\大数据应用系统开发实践\nlp_processing"

python sentiment_trend.py              # 情感趋势
python danmaku_classifier.py           # 弹幕类型
python danmaku_time_distribution.py    # 时间分布
python user_behavior_analysis.py       # 用户行为
python word_cooccurrence.py            # 共现网络
python sentiment_distribution.py       # 情感分布 PNG
```

### 11.2 各自预期输出

**sentiment_trend.py**：
```
情感趋势分析
分桶: 60s
时段   弹幕数   平均得分   主导
0-3min  456     0.68      正面
3-6min  523     0.52      中性
...
保存: sentiment_trend.json
```

**danmaku_classifier.py**：
```
弹幕类型分类
普通类: 1769 (50.34%)
玩梗类:  580 (16.50%)
感叹类:  420 (11.95%)
祝福类:  320 ( 9.11%)
刷屏类:  245 ( 6.97%)
提问类:  181 ( 5.15%)
```

**danmaku_time_distribution.py**：
```
时间分布
0-5min:   892 (25.4%)
5-10min: 1456 (41.4%)
10-15min: 856 (24.4%)
15min+:   310 ( 8.8%)
峰值: 第180秒(3min), 87条
```

**user_behavior_analysis.py**：
```
用户行为
独立用户: 2156
人均弹幕: 1.63
活跃用户(>=3条): 312
最高发言: 15条
```

**word_cooccurrence.py**：
```
共现网络
节点: 50
边: 234
平均度数: 9.36
网络密度: 0.192

高共现词对:
  AI - 模型: 45
  权限 - 安全: 38
  人类 - 智能: 32
```

**sentiment_distribution.py**：
```
生成情感分布饼图...
保存: sentiment_distribution.png
```

### 11.3 测试用例

| 脚本 | 测试项 | 通过条件 |
|------|--------|---------|
| sentiment_trend | 输出时段数 | 4+ 个时段 |
| classifier | 6 种类型 | 6 行分类结果 |
| time_distribution | 4 段 | 0-5/5-10/10-15/15+ |
| user_behavior | 字段齐全 | 用户数/均值/活跃度 |
| cooccurrence | 网络边数 | 100+ 边 |
| sentiment_distribution | PNG 存在 | `os.path.exists('sentiment_distribution.png')` |

---

## 12. 功能 10：前端可视化（ECharts 词云 + 图表）

### 12.1 启动前端

```bash
cd "F:\Claude Project\大数据应用系统开发实践\web_frontend"
python -m http.server 8080
```

> **必须用 HTTP 协议打开**，直接 `file://` 打开会被浏览器同源策略拦截导致 fetch 失败。

### 12.2 访问页面

| 页面 | URL | 内容 |
|------|-----|------|
| 词云展示页 | http://localhost:8080/index.html | 词云 + 时间轴 + 视频信息 |
| 统计图表页 | http://localhost:8080/charts.html | 情感/趋势/类型/用户行为 |

### 12.3 预期效果

**index.html**：
- 顶部显示视频标题、UP 主、播放量
- 中部 ECharts 词云，点击词语弹出相关弹幕
- 底部弹幕时间分布柱状图（带缩略轴）

**charts.html**：
- 4 个核心图表：情感分布饼图、词频 Top20 柱状图、情感趋势双 Y 轴图、弹幕类型分布饼图
- 用户行为卡片：独立用户 / 活跃用户 / 最高发言

### 12.4 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 页面加载 | 200 状态 | 浏览器无 404 |
| 词云渲染 | 出现 80+ 词语 | 视觉检查 |
| 词云交互 | 点击词语弹窗 | 弹窗显示弹幕列表 |
| 时间轴 | 柱状图渲染 | 显示弹幕密度 |
| 图表渲染 | 4 个图表全部可见 | F12 无 JS 错误 |
| DataService | 异步加载 JSON | Network 标签 200 |

### 12.5 浏览器调试

F12 → Console 标签若有错误：

| 错误 | 原因 | 解决 |
|------|------|------|
| `CORS policy` | 用 `file://` 打开 | 用 `http://` 访问 |
| `404 wordfreq.json` | 路径错误 | 确认 `nlp_processing/wordfreq.json` 存在 |
| `echarts is not defined` | ECharts CDN 失败 | 检查网络或换 CDN |

---

## 13. 端到端联调测试

### 13.1 完整流水线脚本

将以下命令保存为 `course_reports/run_e2e_B.sh`：

```bash
#!/bin/bash
set -e
ROOT="F:\Claude Project\大数据应用系统开发实践"

echo "==== 1. 词频统计 + LDA ===="
cd "$ROOT/nlp_processing"
python nlp_process.py
python generate_wordcloud_v2.py

echo "==== 2. 情感分析 ===="
python sentiment_lexicon.py
python sentiment_enhanced.py
python sentiment_distribution.py

echo "==== 3. 增强 NLP 模块 ===="
python segmentation.py
python ner_recognition.py
python keyword_extraction.py

echo "==== 4. 高级分析 ===="
python lda_sentiment_topics.py
python sentiment_trend.py
python danmaku_classifier.py
python danmaku_time_distribution.py
python user_behavior_analysis.py
python word_cooccurrence.py

echo "==== 5. 启动前端 ===="
cd "$ROOT/web_frontend"
python -m http.server 8080 &
SERVER_PID=$!
sleep 2
echo "前端服务已启动: http://localhost:8080  (PID: $SERVER_PID)"
echo "按 Ctrl+C 停止服务"
wait $SERVER_PID
```

### 13.2 一键执行

```bash
cd "F:\Claude Project\大数据应用系统开发实践"
bash course_reports/run_e2e_B.sh
```

### 13.3 联调通过标准

| 阶段 | 关键产物 | 通过条件 |
|------|---------|---------|
| 词频 | wordfreq.json | Top 100 非空 |
| 词云 | wordcloud.json | 100 条数据 |
| 情感 | sentiment.json | 3515 条打分 |
| LDA | lda_topics.json | 8 主题 |
| 增强 | sentiment_enhanced.json + 各类 json | 字段齐全 |
| 前端 | http://localhost:8080 | 浏览器正常渲染 |

---

## 14. 常见问题排查

### Q1. `ModuleNotFoundError: No module named 'pkuseg'`

- **原因**：未安装 pkuseg
- **解决**：`pip install pkuseg`
- **降级**：`segmentation.py` 默认在 pkuseg 不可用时降级为 jieba

### Q2. `SnowNLP` 训练数据找不到

- **原因**：`online_shopping_10_cats.csv` 路径错误
- **解决**：确认该文件在 `nlp_processing/` 下；或在脚本中修改 `BASE_DIR`

### Q3. `gensim` 报 `ImportError: smart_open`

- **原因**：gensim 与 smart_open 版本不兼容
- **解决**：`pip install smart_open==6.3.0`

### Q4. 前端页面空白 / 图表不显示

- **原因 1**：用 `file://` 直接打开被 CORS 拦截
- **解决**：用 `python -m http.server` 启动
- **原因 2**：JSON 文件路径错误
- **解决**：检查 `js/data.js` 中 `loadJSON()` 的 basePath

### Q5. 词云只有少量词

- **原因**：`wordfreq.json` 中 Top 100 数量过少
- **解决**：先跑通 `nlp_process.py` 生成 `wordfreq.json`

### Q6. LDA coherence 很低（< 0.3）

- **原因**：数据量小（< 1000 条）或停用词过多
- **解决**：放宽 `nlp_process.py` 中的 `min_freq` 阈值；或合并相近弹幕

### Q7. 时间分布图 Y 轴数值异常大

- **原因**：分桶粒度过细
- **解决**：调整 `danmaku_time_distribution.py` 中 `bucket_size=30` 为 `60` 或 `120`

### Q8. 情感分布全部归为中性

- **原因**：SnowNLP 模型未训练好
- **解决**：使用项目自带的 `sentiment_model.marshal.3`；或在 `sentiment_lexicon.py` 顶部强制指定

---

## 附录：相关文件路径速查

| 文件 | 路径 |
|------|------|
| 分词模块 | [nlp_processing/segmentation.py](../nlp_processing/segmentation.py) |
| 词频 + LDA | [nlp_processing/nlp_process.py](../nlp_processing/nlp_process.py) |
| 词云生成 | [nlp_processing/generate_wordcloud_v2.py](../nlp_processing/generate_wordcloud_v2.py) |
| 情感分析（基础） | [nlp_processing/sentiment_lexicon.py](../nlp_processing/sentiment_lexicon.py) |
| 情感分析（增强） | [nlp_processing/sentiment_enhanced.py](../nlp_processing/sentiment_enhanced.py) |
| NER 识别 | [nlp_processing/ner_recognition.py](../nlp_processing/ner_recognition.py) |
| 关键词抽取 | [nlp_processing/keyword_extraction.py](../nlp_processing/keyword_extraction.py) |
| 情感分离 LDA | [nlp_processing/lda_sentiment_topics.py](../nlp_processing/lda_sentiment_topics.py) |
| 情感趋势 | [nlp_processing/sentiment_trend.py](../nlp_processing/sentiment_trend.py) |
| 弹幕类型 | [nlp_processing/danmaku_classifier.py](../nlp_processing/danmaku_classifier.py) |
| 时间分布 | [nlp_processing/danmaku_time_distribution.py](../nlp_processing/danmaku_time_distribution.py) |
| 用户行为 | [nlp_processing/user_behavior_analysis.py](../nlp_processing/user_behavior_analysis.py) |
| 共现网络 | [nlp_processing/word_cooccurrence.py](../nlp_processing/word_cooccurrence.py) |
| 情感分布图 | [nlp_processing/sentiment_distribution.py](../nlp_processing/sentiment_distribution.py) |
| 词云展示页 | [web_frontend/index.html](../web_frontend/index.html) |
| 统计图表页 | [web_frontend/charts.html](../web_frontend/charts.html) |
| DataService | [web_frontend/js/data.js](../web_frontend/js/data.js) |
| 课程设计报告 | [报告B_应用层.md](报告B_应用层.md) |
