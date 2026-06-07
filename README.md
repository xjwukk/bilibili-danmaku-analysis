# B站弹幕数据分析系统

## 项目概述

本项目是一个针对B站视频弹幕数据的完整数据分析系统，包含数据采集、NLP处理、大数据存储和前端可视化四个模块。

**目标视频**: BV1jEAaz3E6K (一个视频搞懂OpenClaw！) - 518万播放，5400+弹幕

**技术栈**: Python + requests/Protobuf + jieba/pkuseg + SnowNLP + Gensim + HBase + ECharts

---

## 目录结构

```
.
├── CLAUDE.md                          # Claude Code 项目指导文件
├── 参考.md                            # 参考资料
│
├── bilibili_crawler/                    # 数据采集模块
│   ├── README.md                      # 爬虫说明文档
│   ├── bilibili_crawler.py            # 爬虫主程序
│   ├── bilibili_data.json             # 爬取的原始数据
│   └── requirements.txt               # Python依赖
│
├── nlp_processing/                        # NLP处理模块
│   ├── clean_danmaku.py               # 数据清洗
│   ├── segmentation.py                 # 中文分词（pkuseg/jieba）
│   ├── nlp_process.py                 # NLP综合处理流水线
│   ├── sentiment_lexicon.py            # 情感分析（SnowNLP + 词典）
│   ├── sentiment_rules.py             # 情感分析（规则 + 词典）
│   ├── lda_sentiment_topics.py        # LDA主题建模
│   ├── ner_recognition.py             # 命名实体识别
│   ├── keyword_extraction.py          # 关键词抽取
│   ├── generate_wordcloud.py          # 词云生成
│   ├── cn_stopwords.txt               # 中文停用词表
│   ├── sentiment_model.marshal.3      # 训练后的SnowNLP模型
│   ├── online_shopping_10_cats.csv   # 电商评论训练数据
│   ├── cleaned_danmaku.json           # 清洗后弹幕数据
│   ├── wordfreq.json                  # 词频统计结果
│   ├── sentiment.json                 # 情感分析结果
│   ├── sentiment_rules.json           # 规则情感分析结果
│   ├── lda_topics.json                # LDA主题结果
│   ├── lda_sentiment_topics.json      # 情感分离LDA主题
│   ├── keywords.json                  # 关键词抽取结果
│   ├── ner_entities.json              # NER实体识别结果
│   ├── sentiment_distribution.json    # 情感分布统计
│
├── hbase_storage/                     # 大数据存储模块
│   ├── README.md                      # 存储方案说明
│   ├── HBASE_SCHEMA.md                # HBase表结构设计
│   ├── hbase_writer.py               # 数据写入工具
│   ├── hbase_query.py                # 数据查询工具
│   ├── hbase_simulator.py            # HBase模拟测试工具
│   └── wordfreq_mapreduce.py         # MapReduce词频统计
│
├── web_frontend/                    # 前端可视化模块
│   ├── index.html                    # 主页面
│   ├── css/
│   │   └── style.css                # Kaggle风格样式
│   └── js/
│       ├── data.js                  # 数据服务层
│       ├── charts.js                 # 图表管理器
│       ├── wordcloud.js              # 词云组件
│       └── timeline.js                # 时间轴组件
│
├── course_reports/                      # 课程设计报告
│   ├── 报告A_数据层.md                # 学生A报告（爬虫+数据清洗+HBase存储）
│   └── 报告B_应用层.md                # 学生B报告（NLP处理+前端可视化）
│
├── 大数据应用系统开发实践-任务书1.docx
└── 大数据应用系统开发实践-报告模板-每位同学提交.doc
```

---

## 模块分工

| 模块 | 负责学生 | 主要职责 |
|------|---------|---------|
| bilibili_crawler | 学生A（数据层） | B站API爬虫、Protobuf解析、数据清洗 |
| hbase_storage | 学生A（数据层） | HBase表设计、数据读写、MapReduce |
| nlp_processing | 学生B（应用层） | 分词、词频统计、情感分析、LDA主题、NER、关键词抽取、词云生成 |
| web_frontend | 学生B（应用层） | ECharts词云、统计图表、前端交互 |
| course_reports | 全体 | 学生A撰写数据层报告，学生B撰写应用层报告 |

---

## 快速开始

### 1. 数据采集

```bash
cd bilibili_crawler
# 配置Cookie后运行
python bilibili_crawler.py
```

### 2. NLP处理

```bash
cd nlp_processing

# 基础NLP流程
python clean_danmaku.py           # 清洗弹幕
python nlp_process.py            # 分词+词频+情感+LDA
python generate_wordcloud.py     # 生成词云

# 扩展分析
python sentiment_rules.py        # 规则情感分析
python ner_recognition.py       # NER实体识别
python keyword_extraction.py     # 关键词抽取
```

### 3. 前端展示

```bash
cd web_frontend
python -m http.server 8080
# 访问 http://localhost:8080/index.html
```

---

## 数据流程

```
B站视频
    │
    ▼
┌─────────────┐    bilibili_data.json
│ 爬虫采集    │ ──────────────────► nlp_processing/
└─────────────┘                      │
                                     ▼
                              ┌───────────┐
                              │ 数据清洗  │ cleaned_danmaku.json
                              └───────────┘
                                     │
                                     ▼
                              ┌───────────┐
                              │  NLP处理  │ wordfreq.json, sentiment.json,
                              └───────────┘ lda_topics.json, keywords.json
                                     │
                         ┌───────────┴───────────┐
                         ▼                       ▼
                  ┌─────────────┐          ┌──────────────┐
                  │  词云生成   │          │  深度分析    │
                  │ (ECharts)  │          │ 时间分布/用户 │
                  └─────────────┘          │ 行为/类型分类│
                                           └──────────────┘
                                                 │
                                                 ▼
                                          web_frontend/
                                          (前端可视化)
```

---

## 输出文件说明

### 核心数据文件

| 文件 | 说明 |
|------|------|
| `cleaned_danmaku.json` | 清洗后弹幕（3515条） |
| `wordfreq.json` | 词频Top100 |
| `sentiment.json` | 情感分析结果 |
| `lda_topics.json` | LDA主题模型 |
| `danmaku_classified.json` | 弹幕类型分类 |
| `sentiment_trend.json` | 情感趋势 |
| `user_behavior.json` | 用户行为分析 |
| `word_cooccurrence.json` | 词语共现网络 |

### 数据规模

| 指标 | 数值 |
|------|------|
| 原始弹幕 | 5,656条 |
| 清洗后弹幕 | 3,515条 |
| 分词总词数 | 11,623 |
| 不重复词数 | 4,105 |
| LDA主题数 | 8个 |
| 弹幕类型 | 8类 |
| 独立用户 | 2,156个 |
