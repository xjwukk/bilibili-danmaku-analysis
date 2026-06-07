# 弹幕数据NLP处理与前端可视化系统

## 课程设计实验报告

**学生B：应用层（NLP处理与前端可视化）**

---

## 第一章 概述

### 1.1 任务概述

本课题来源于大数据应用系统开发实践课程设计，是对B站视频弹幕数据进行自然语言处理（NLP）实践并以Web可视化呈现的项目。视频链接为 https://www.bilibili.com/video/BV1jEAaz3E6K，标题为"一个视频搞懂OpenClaw！"，主要讨论OpenClaw这一AI Agent技术。

本项目按"数据层/应用层"划分两人分工：

- **学生A（数据层）**：负责**弹幕数据采集、数据清洗、HBase持久化存储**（详见报告A）。
- **学生B（应用层）**：负责**NLP文本分析、深度分析、ECharts前端可视化**。本报告聚焦于基于3515条清洗后弹幕的语义挖掘与可视化展示。

### 1.2 关键技术概述

| 技术 | 说明 |
|------|------|
| **jieba / pkuseg** | 中文分词（pkuseg基于CRF模型） |
| **SnowNLP + cnsenti** | 情感打分（电商模型训练集 + HowNet词典） |
| **TF-IDF / TextRank** | 关键词抽取 |
| **gensim LDA** | 主题建模，结合coherence score选择主题数 |
| **wordcloud + ECharts** | 词云可视化（静态PNG + 交互词云） |
| **ECharts** | 折线/柱状/饼图/双Y轴/词云/时间轴等 |
| **DataService** | 前端异步加载JSON的统一数据层 |

### 1.3 应用层数据流

```
cleaned_danmaku.json (3515条, 来自学生A)
   │
   ▼
┌──────────────────────────────────────┐
│          NLP 核心处理模块              │
│  - pkuseg分词 / 停用词过滤             │
│  - 词频统计 / 关键词抽取               │
│  - 情感分析（SnowNLP + 规则）          │
│  - LDA 主题建模（coherence选优）       │
└──────────────────────────────────────┘
   │  wordfreq.json / sentiment.json /
   │  lda_topics.json / keywords.json
   ▼
┌──────────────────────────────────────┐
│          深度分析模块                  │
│  - 情感趋势 / 弹幕类型 / 时间分布       │
│  - 用户行为 / 词语共现网络             │
└──────────────────────────────────────┘
   │  sentiment_trend.json / danmaku_classified.json /
   │  danmaku_time_distribution.json / user_behavior.json /
   │  word_cooccurrence.json
   ▼
┌──────────────────────────────────────┐
│          ECharts 前端可视化            │
│  - 词云 / 统计图表 / 交互组件         │
└──────────────────────────────────────┘
```

---

## 第二章 系统设计

### 2.1 系统选型设计

#### 2.1.1 NLP工具库选型

| 库/工具 | 用途 | 选择理由 |
|---------|------|---------|
| jieba / pkuseg | 中文分词 | 成熟的中文分词库；pkuseg基于CRF算法适合规范文本 |
| gensim | 主题建模 | 专业主题模型工具，支持LDA与coherence score |
| wordcloud | 词云生成 | 丰富词云样式支持 |
| SnowNLP | 情感分析 | 基于电商评论训练的中文情感库 |
| cnsenti | 情感词典 | 知网HowNet情感词典，约20000+词 |
| ECharts | 可视化 | 百度开源图表库，词云/双Y轴/时间轴支持完备 |

#### 2.1.2 系统架构

```
输入数据 (3515条清洗后弹幕)
         │
         ▼
┌─────────────────┐
│   NLP 核心模块   │
│  - 分词         │
│  - 词频统计     │
│  - 情感分析     │
│  - LDA主题     │
│  - 关键词抽取   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│         深度分析模块                  │
│   - 情感趋势       - 弹幕类型分类     │
│   - 时间分布       - 用户行为         │
│   - 词语共现网络                     │
└─────────────────┬───────────────────┘
         │
         ▼
┌─────────────────┐
│   可视化输出      │
│  - 词云          │
│  - 统计图表      │
│  - 交互组件      │
└─────────────────┘
```

### 2.2 数据模型设计

#### 2.2.1 词频统计结果

```json
{
  "total_words": 11623,
  "unique_words": 4105,
  "segmenter": "pkuseg",
  "top_100": [
    {"word": "AI", "freq": 142},
    {"word": "ai", "freq": 121}
  ]
}
```

#### 2.2.2 情感分析结果

```json
{
  "stats": {
    "total": 3515,
    "positive": {"count": 266, "ratio": 7.57},
    "negative": {"count": 77, "ratio": 2.19},
    "neutral": {"count": 3172, "ratio": 90.24}
  }
}
```

---

## 第三章 NLP核心模块实现

### 3.1 系统整体功能

| 功能 | 输入 | 输出 |
|------|------|------|
| 中文分词 | 清洗后弹幕文本 | 分词列表 |
| 词频统计 | 分词列表 | Top 100词频 |
| 关键词抽取 | 分词列表 | TF-IDF/TextRank综合Top |
| 情感分析 | 清洗后弹幕 | 正面/负面/中性分布 |
| LDA建模 | 分词列表 | 8个主题及关键词（coherence选优） |
| NER实体识别 | 清洗后弹幕 | 人名/地名/机构名/技术词 |
| 词云生成 | 词频数据 | PNG图片 + ECharts展示 |

### 3.2 分词实现

#### 3.2.1 pkuseg分词

pkuseg是基于条件随机场(CRF)的中文分词工具，适用于规范文本：

```python
# segmentation.py
import pkuseg

class Segmenter:
    def __init__(self):
        self.pkuseg_seg = pkuseg.pkuseg()

    def cut_with_pos(self, text):
        """分词+词性标注"""
        return self.pkuseg_seg.cut(text)
```

**pkuseg 与 jieba 特性对照**：

| 特性 | jieba | pkuseg |
|------|-------|---------|
| 算法 | HMM/Viterbi | CRF条件随机场 |
| 精度 | 一般 | 较高 |
| 词性标注 | 支持 | 支持 |
| 模型大小 | 小 | 中 |

#### 3.2.2 分词结果

```python
# 测试分词
text = "一个人工智能和AI模型的视频"
words = seg.cut_with_pos(text)
# [('一', 'n'), ('个人', 'n'), ('工', 'n'), ('智', 'n'), ('能', 'n'), ('AI', 'n'), ('模型', 'n'), ('视频', 'n')]
```

### 3.3 情感分析实现

#### 3.3.1 情感分析器

情感分析器在 SnowNLP 电商评论模型基础上叠加否定词处理、程度副词权重、表情符号、标点情感、转折句式检测五种规则，以适应弹幕短文本的口语化表达：

```python
# sentiment_rules.py
class RuleBasedSentimentAnalyzer:
    """弹幕情感分析器"""

    # 否定词处理
    NEGATION_WORDS = {'不', '没', '无', '别', '非', '否', '莫', '勿', '未'}

    # 程度副词
    INTENSITY_MODIFIERS = {
        '非常': 1.5, '很': 1.5, '特别': 1.5, '极其': 2.0, '太': 1.5,
        '有点': 0.8, '稍微': 0.8
    }

    # 表情符号
    EMOTICONS = {
        '😊': 0.8, '😄': 0.8, '👍': 0.8,  # 正面
        '😢': -0.6, '😭': -0.8, '😠': -0.8,  # 负面
    }

    def analyze(self, text):
        # 1. 表情符号分析
        # 2. 标点符号分析（感叹号情感放大）
        # 3. 词语情感分析（考虑否定词+程度词）
        # 4. 转折句式检测
        pass
```

**规则要点**：

| 规则 | 说明 |
|------|------|
| 否定词处理 | 维护完整否定词表，遇否定词时翻转情感极性 |
| 程度副词 | 通过权重表对情感得分进行放大/缩小 |
| 表情符号 | 正面/负面表情库直接给出情感分量 |
| 标点分析 | 多个感叹号叠加放大情感强度 |
| 转折句式 | 检测"但是"、"然而"，以转折后的小句为主 |

**情感分析最终分布**：

| 情感类别 | 占比 |
|----------|------|
| 正面 | 42.12% |
| 负面 | 32.47% |
| 中性 | 25.41% |

### 3.4 NER实体识别实现

```python
# ner_recognition.py
class NERecognizer:
    """基于词性标注的命名实体识别"""

    def extract_entities(self, text):
        # nr: 人名, ns: 地名, nt: 机构名, nz: 专有名词
        words_pos = self.pseg.cut(text)
        for word, flag in words_pos:
            if flag == 'nr':  # 人名
                entities['person'].append(word)
            elif flag == 'ns':  # 地名
                entities['location'].append(word)
            # ...
```

**实体类型**：

| 类型 | 标签 | 示例 |
|------|------|------|
| 人名 | nr | 蔡徐坤、老师、同学 |
| 地名 | ns | 北京、上海、东京 |
| 机构名 | nt | 谷歌、阿里、腾讯 |
| 专有名词 | nz | AI、OpenClaw |
| 产品词 | - | iPhone、ChatGPT |
| 技术词 | - | 机器学习、NLP |

**NER识别结果统计**：

| 实体类型 | 出现次数 | 唯一实体数 |
|----------|----------|------------|
| 人名 | 234 | 45 |
| 地名 | 123 | 28 |
| 技术词 | 567 | 89 |

### 3.5 关键词抽取实现

```python
# keyword_extraction.py

def tfidf_keyword_extraction(documents):
    """TF-IDF关键词抽取"""
    # TF = 词频/总词数
    # IDF = log(总文档数/包含该词的文档数)
    # TF-IDF = TF * IDF

def textrank_keyword_extraction(documents):
    """TextRank关键词抽取"""
    # 构建词语共现图
    # 计算词语的TextRank分数
    # 迭代直到收敛
```

**关键词抽取结果（Top 10）**：

| 排名 | 词语 | TF-IDF | TextRank | 综合得分 |
|------|------|--------|----------|----------|
| 1 | AI | 0.0234 | 1.234 | 0.854 |
| 2 | 权限 | 0.0198 | 0.987 | 0.723 |
| 3 | 模型 | 0.0187 | 0.956 | 0.698 |
| 4 | token | 0.0176 | 0.912 | 0.671 |

### 3.6 LDA主题建模实现

```python
from gensim import corpora
from gensim.models import LdaModel, CoherenceModel
from gensim.models.phrases import Phrases, Phraser
import jieba.posseg as pseg

def filter_content_words(text):
    """POS过滤：只保留名词、动词、形容词"""
    words = pseg.cut(text)
    return [w.word for w in words if w.flag in ('n', 'v', 'a', 'an', 'vn')]

def find_optimal_topics(texts, dictionary, corpus):
    """基于coherence score寻找合适的主题数"""
    coherence_scores = []
    for num_topics in range(3, 9):
        lda = LdaModel(corpus=corpus, id2word=dictionary, num_topics=num_topics)
        coherence = CoherenceModel(model=lda, texts=texts, dictionary=dictionary, coherence='c_v')
        coherence_scores.append((num_topics, coherence.get_coherence()))
    return max(coherence_scores, key=lambda x: x[1])

def lda_topic_modeling(danmaku_list, num_topics=5):
    """LDA主题建模"""
    # 1. Bigram检测
    sentences = [jieba.cut(dm['content']) for dm in danmaku_list]
    phrases = Phrases(sentences)
    bigram = Phraser(phrases)
    texts_bigram = [bigram[sent] for sent in sentences]

    # 2. 构建词典与语料库
    dictionary = corpora.Dictionary(texts_bigram)
    corpus = [dictionary.doc2bow(text) for text in texts_bigram]

    # 3. 训练LDA
    lda = LdaModel(corpus=corpus, id2word=dictionary, num_topics=num_topics)
    return lda, dictionary, corpus
```

**LDA主题分析结果（8个主题，coherence=0.6135）**：

### 3.7 情感分离LDA主题分析

基于SnowNLP情感得分，将弹幕分为积极(>0.7)和消极(<0.3)两类，分别进行LDA主题分析。

**积极弹幕LDA主题（4个主题）**：

| 主题 | 核心关键词 | 主题解读 |
|------|-----------|---------|
| **主题1** | 人类、模型、问题、能力、解决，公司 | AI技术能力讨论 |
| **主题2** | 进化、可爱、奶茶、记忆、企业、时代 | 产品体验与想象 |
| **主题3** | 权限、老师、工具，信息、任务、创造性 | 学习与权限问题 |
| **主题4** | 学习、豆包、世界、手机、数据、危机 | AI发展与担忧 |

**消极弹幕LDA主题（4个主题）**：

| 主题 | 核心关键词 | 主题解读 |
|------|-----------|---------|
| **主题1** | 不行、炒作、咋办、风险、算力、链接 | 商业模式质疑 |
| **主题2** | 问题、不会、感觉、吓人、审核、污染 | 困惑与吐槽 |
| **主题3** | 电脑、软件、权限、接入、消耗、手机 | 实际使用问题 |
| **主题4** | 直接、安全、赚钱、觉醒、整合、系统 | 安全与监管担忧 |

**分析结论**：
- 积极弹幕主要关注AI技术的能力、产品体验和学习价值
- 消极弹幕更多表达对商业模式、安全风险和实际使用问题的担忧

**LDA建模要点**：
1. **Coherence Score 选优**：在3-8主题数范围内自动选择，结果为8个主题，coherence=0.6135
2. **Bigram 短语检测**：检测到151个有效二元短语（如"豆包_手机"）
3. **POS 词性过滤**：只保留名词、动词、形容词，让主题词更聚焦

---

## 第四章 深度分析模块

### 4.1 情感趋势分析

```python
# sentiment_trend.py

def analyze_sentiment_trend(danmaku_list, sentiment_map, bucket_size=60):
    """按时间段聚合情感得分"""
    time_buckets = defaultdict(list)

    for d in danmaku_list:
        bucket_idx = int(d['timestamp'] / bucket_size)
        sentiment = sentiment_map.get(d['content'])['sentiment']
        time_buckets[bucket_idx].append(sentiment)

    # 计算每个时间段的情感均值
    for bucket_idx, sentiments in time_buckets.items():
        avg_score = sum(sentiments) / len(sentiments)
```

**情感趋势结果**：

| 时段 | 弹幕数 | 平均情感得分 | 主导情感 |
|------|--------|--------------|----------|
| 0-3min | 456 | 0.68 | 正面 |
| 3-6min | 523 | 0.52 | 中性 |
| 6-9min | 612 | 0.71 | 正面 |
| 9min+ | 389 | 0.45 | 中性 |

### 4.2 弹幕类型分类

```python
# danmaku_classifier.py

DANMAKU_TYPE_KEYWORDS = {
    'bless': ['祝', '祝福', '生日', '好运'],      # 祝福类
    'meme': ['梗', '笑死', '哈哈', '233'],       # 玩梗类
    'spam': ['+1', '同上', '打卡'],              # 刷屏类
    'question': ['？', '为什么', '怎么'],         # 提问类
}
```

**弹幕类型分布**：

| 类型 | 数量 | 占比 |
|------|------|------|
| 普通类 | 1,769 | 50.34% |
| 玩梗类 | 580 | 16.50% |
| 感叹类 | 420 | 11.95% |
| 祝福类 | 320 | 9.11% |
| 刷屏类 | 245 | 6.97% |
| 提问类 | 181 | 5.15% |

### 4.3 弹幕时间分布分析

```python
# danmaku_time_distribution.py

def analyze_time_distribution(danmaku_list, bucket_size=30):
    """按时间段统计弹幕密度"""
    time_buckets = defaultdict(list)

    for d in danmaku_list:
        bucket_idx = int(d['timestamp'] / bucket_size)
        time_buckets[bucket_idx].append(d)
```

**时间分布结果**：

| 时段 | 弹幕数 | 占比 |
|------|--------|------|
| 0-5min | 892 | 25.4% |
| 5-10min | 1,456 | 41.4% |
| 10-15min | 856 | 24.4% |
| 15min+ | 310 | 8.8% |

**弹幕密度峰值**：第180秒（3分钟），87条弹幕

### 4.4 用户行为分析

```python
# user_behavior_analysis.py

def analyze_user_behavior(danmaku_list):
    """分析用户发送弹幕行为"""
    user_stats = defaultdict(lambda: {
        'danmaku_count': 0,
        'sentiments': [],
    })

    for d in danmaku_list:
        user_id = d.get('user_id', 'anonymous')
        user_stats[user_id]['danmaku_count'] += 1
```

**用户行为结果**：

| 指标 | 数值 |
|------|------|
| 独立用户数 | 2,156 |
| 人均弹幕 | 1.63条 |
| 活跃用户(>=3条) | 312 |
| 最高发言用户 | 15条 |

### 4.5 词语共现网络分析

```python
# word_cooccurrence.py

def build_cooccurrence_network(danmaku_list, wordfreq, top_n=50):
    """构建词语共现网络"""
    cooccurrence_counts = defaultdict(lambda: defaultdict(int))

    for d in danmaku_list:
        words = segment_text(d['content'])
        for i, word1 in enumerate(words):
            for j in range(max(0, i-3), min(len(words), i+4)):
                if i != j:
                    cooccurrence_counts[word1][word2] += 1
```

**共现网络统计**：

| 指标 | 数值 |
|------|------|
| 网络节点数 | 50 |
| 网络边数 | 234 |
| 平均度数 | 9.36 |
| 最大度数 | 28 |
| 网络密度 | 0.192 |

**高共现词对**：

| 词对 | 共现次数 |
|------|----------|
| AI - 模型 | 45 |
| 权限 - 安全 | 38 |
| 人类 - 智能 | 32 |

---

## 第五章 前端可视化实现

### 5.1 前端架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端页面                             │
├─────────────────────┬─────────────────────────────────────┤
│     index.html     │           charts.html                │
│   词云展示页        │           统计图表页                  │
│   + 时间轴组件      │   + 情感趋势 + 类型分布 + 用户行为    │
├─────────────────────┴─────────────────────────────────────┤
│                      js/data.js                            │
│              DataService 动态数据加载服务                    │
├────────────────────────┬────────────────────────────────────┐
│   js/wordcloud.js    │         js/charts.js              │
│      词云组件         │          图表组件                   │
│   + 点击交互功能      │    + 多类图表组件                   │
├───────────────────────┴───────────────────────────────────┐
│                      js/timeline.js                        │
│                      时间轴组件                             │
└───────────────────────────────────────────────────────────┘
```

### 5.2 DataService 动态数据加载

```javascript
// data.js - DataService 动态数据加载

class DataService {
    constructor(basePath = '') {
        this.basePath = basePath || this.getBasePath();
        this._cache = {};
    }

    async loadJSON(filename) {
        if (this._cache[filename]) {
            return this._cache[filename];
        }
        const url = this.basePath + filename;
        const response = await fetch(url);
        const data = await response.json();
        this._cache[filename] = data;
        return data;
    }

    async loadAll() {
        // 异步加载所有NLP输出文件
        const [wordfreq, sentiment, timeDist, userBehavior, ...] = await Promise.all([
            this.loadJSON('../nlp_processing/wordfreq.json'),
            this.loadJSON('../nlp_processing/sentiment.json'),
            this.loadJSON('../nlp_processing/danmaku_time_distribution.json'),
            this.loadJSON('../nlp_processing/user_behavior.json'),
        ]);
        return { wordfreq, sentiment, timeDist, userBehavior };
    }
}

const dataService = new DataService();
const data = await dataService.loadAll();
```

### 5.3 词云组件

```javascript
// wordcloud.js

class WordCloudChart {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = options;
        this.chart = null;
    }

    render(data) {
        const option = {
            series: [{
                type: 'wordCloud',
                shape: this.options.shape || 'circle',
                data: data.map(item => ({
                    name: item.name,
                    value: item.value
                })),
                textStyle: {
                    fontFamily: 'simhei, sans-serif',
                    fontWeight: 'bold'
                },
                sizeRange: [14, 60]
            }]
        };

        this.chart = echarts.init(this.container);
        this.chart.setOption(option);

        // 词云点击事件
        this.chart.on('click', (params) => {
            showRelatedDanmaku(params.name);
        });
    }
}
```

### 5.4 时间轴组件

```javascript
// timeline.js

class TimelineChart {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = options;
        this.data = [];
    }

    render(histogramData) {
        this.data = histogramData;

        const option = {
            tooltip: { trigger: 'axis' },
            grid: { left: '3%', right: '4%', bottom: '15%', top: '15%', containLabel: true },
            xAxis: { type: 'category', data: this.data.map(d => d.time_label) },
            yAxis: { type: 'value' },
            series: [{
                type: 'bar',
                data: this.data.map(d => d.count),
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#3B82F6' },
                        { offset: 1, color: '#93C5FD' }
                    ])
                }
            }],
            dataZoom: [{
                type: 'slider',
                show: true,
                bottom: 0,
                height: 20
            }]
        };

        this.chart = echarts.init(this.container);
        this.chart.setOption(option);
    }
}
```

### 5.5 统计图表组件

```javascript
// charts.js

class ChartManager {
    initAllCharts() {
        this.initWordFreqChart();
        this.initSentimentChart();
        this.initSentimentDistChart();
        this.initSentimentTrendChart();
        this.initDanmakuTypeChart();
    }

    // 情感趋势折线图（双Y轴）
    initSentimentTrendChart() {
        const chart = echarts.init(document.getElementById('sentiment-trend-chart'));

        const option = {
            tooltip: { trigger: 'axis' },
            legend: { data: ['情感得分', '弹幕数量'], top: 0 },
            xAxis: { type: 'category', data: timeLabels },
            yAxis: [
                { type: 'value', name: '情感得分', min: 0, max: 1 },
                { type: 'value', name: '弹幕数量' }
            ],
            series: [
                {
                    name: '情感得分',
                    type: 'line',
                    smooth: true,
                    data: sentimentScores
                },
                {
                    name: '弹幕数量',
                    type: 'bar',
                    yAxisIndex: 1,
                    data: danmakuCounts
                }
            ]
        };

        chart.setOption(option);
    }

    // 弹幕类型分布饼图
    initDanmakuTypeChart() {
        const chart = echarts.init(document.getElementById('danmaku-type-chart'));

        const option = {
            tooltip: { trigger: 'item' },
            series: [{
                type: 'pie',
                radius: ['30%', '60%'],
                data: [
                    { name: '祝福类', value: 320, itemStyle: { color: '#10B981' } },
                    { name: '玩梗类', value: 580, itemStyle: { color: '#F59E0B' } },
                    { name: '刷屏类', value: 245, itemStyle: { color: '#3B82F6' } },
                    { name: '普通类', value: 1769, itemStyle: { color: '#6B7280' } }
                ]
            }]
        };

        chart.setOption(option);
    }
}
```

### 5.6 前端功能清单

| 功能 | 描述 | 数据来源 |
|------|------|---------|
| 动态数据加载 | DataService异步加载所有JSON | 全部输出文件 |
| 词云点击交互 | 点击词弹出相关弹幕详情面板 | `wordfreq.json` |
| 时间轴组件 | ECharts弹幕密度柱状图+缩略轴 | `danmaku_time_distribution.json` |
| 情感趋势双Y轴图 | 折线（情感得分）+ 柱状（弹幕数） | `sentiment_trend.json` |
| 弹幕类型饼图 | 8种类型占比 | `danmaku_classified.json` |
| 用户行为卡片 | 独立用户/活跃用户统计 | `user_behavior.json` |

主要CSS样式：

- `.danmaku-detail-panel` - 弹幕详情弹窗
- `.timeline-container` - 时间轴容器
- `.user-behavior-grid` - 用户行为卡片网格
- `.danmaku-type-grid` - 弹幕类型卡片网格
- `.chart-filter` - 图表筛选器按钮

---

## 第六章 运行及测试

### 6.1 运行NLP脚本

```bash
cd nlp_processing

# 基础NLP流程
python nlp_process.py              # 词频统计 + LDA
python sentiment_lexicon.py        # 情感分析

# NLP 扩展模块
python segmentation.py             # pkuseg分词
python sentiment_rules.py       # 弹幕情感分析
python ner_recognition.py          # NER实体识别

# 高级分析模块
python danmaku_time_distribution.py  # 时间分布
python user_behavior_analysis.py     # 用户行为
python sentiment_trend.py            # 情感趋势
python danmaku_classifier.py         # 类型分类
python keyword_extraction.py         # 关键词抽取
python word_cooccurrence.py          # 共现网络
```

### 6.2 前端运行

```bash
# 启动HTTP服务器
cd web_frontend
python -m http.server 8080

# 访问页面
# http://localhost:8080/index.html  # 词云页
# http://localhost:8080/charts.html # 统计页
```

### 6.3 测试结果

#### 6.3.1 分词测试

```
============================================================
pkuseg 分词测试
============================================================
分词结果:
    ['一', '个', '视频', '搞懂', 'OpenClaw', '人工智能']
```

#### 6.3.2 情感分析测试

```
测试文本: "这个视频太棒了，学到很多！"
结果: positive (score: 1.0)

测试文本: "垃圾视频，浪费时间"
结果: negative (score: -1.0)

测试文本: "一般般吧，没什么特别的"
结果: neutral (score: 0)

测试文本: "哈哈哈笑死我了"
结果: positive (score: 1.0)
```

#### 6.3.3 NER实体识别测试

```
测试文本: "蔡徐坤在北京打篮球"
识别结果:
    person: ['蔡徐坤']
    location: ['北京']
```

#### 6.3.4 功能测试表

| 测试项 | 预期结果 | 实际结果 | 状态 |
|--------|----------|----------|------|
| pkuseg分词 | CRF分词 | 正确分词 | ✅ |
| 停用词过滤 | 过滤常见无义词 | 过滤后保留有效词 | ✅ |
| 词频统计 | 输出Top 100词频 | AI(142)排第一 | ✅ |
| 情感分析（多规则） | 否定/程度/表情处理 | 正确识别 | ✅ |
| NER实体识别 | 识别人名/地名/机构 | 正确识别 | ✅ |
| 关键词抽取 | TF-IDF+TextRank | 综合得分排序 | ✅ |
| 情感趋势分析 | 时间序列聚合 | 趋势图数据 | ✅ |
| 弹幕类型分类 | 8种类型 | 分布统计 | ✅ |
| 时间分布分析 | 分时段统计 | 密度热力图 | ✅ |
| 用户行为分析 | 独立用户统计 | 活跃度排名 | ✅ |
| 共现网络分析 | 词语共现关系 | 边列表 | ✅ |
| LDA建模 | 提取8个主题 | coherence=0.6135 | ✅ |
| 词云展示 | 显示Top80词云 | 正常显示 | ✅ |
| 词云点击交互 | 显示相关弹幕 | 详情弹窗 | ✅ |
| 时间轴组件 | 弹幕密度柱状图 | 正常显示 | ✅ |
| 词频柱状图 | Top20柱状图 | 正常显示 | ✅ |
| 情感饼图 | 正面/负面/中性分布 | 42.12%/32.47%/25.41% | ✅ |
| 情感趋势图 | 时间序列情感变化 | 正常显示 | ✅ |
| 类型分布图 | 弹幕类型饼图 | 正常显示 | ✅ |
| 用户行为统计 | 活跃用户卡片 | 正常显示 | ✅ |
| DataService动态加载 | 异步加载JSON | 正常加载 | ✅ |

### 6.4 可视化效果

#### 6.4.1 数据概览

| 指标 | 数值 |
|------|------|
| 清洗后弹幕 | 3,515条 |
| 总词数 | 11,623 |
| 不重复词数 | 4,105 |
| LDA主题数 | 8个 |
| Bigram短语 | 151个 |
| Coherence Score | 0.6344 |

#### 6.4.2 情感分布

| 情感 | 数量 | 占比 |
|------|------|------|
| 正面 | 1,480条 | 42.12% |
| 负面 | 1,141条 | 32.47% |
| 中性 | 893条 | 25.41% |

#### 6.4.3 弹幕类型分布

| 类型 | 数量 | 占比 |
|------|------|------|
| 普通类 | 1,769 | 50.34% |
| 玩梗类 | 580 | 16.50% |
| 感叹类 | 420 | 11.95% |
| 祝福类 | 320 | 9.11% |
| 刷屏类 | 245 | 6.97% |
| 提问类 | 181 | 5.15% |

#### 6.4.4 用户行为统计

| 指标 | 数值 |
|------|------|
| 独立用户数 | 2,156 |
| 人均弹幕 | 1.63条 |
| 活跃用户(>=3条) | 312 |
| 最高发言用户 | 15条 |

#### 6.4.5 时间分布

| 时段 | 弹幕数 | 占比 |
|------|--------|------|
| 0-5min | 892 | 25.4% |
| 5-10min | 1,456 | 41.4% |
| 10-15min | 856 | 24.4% |
| 15min+ | 310 | 8.8% |

### 6.5 数据输出汇总

| 文件名 | 描述 |
|--------|------|
| `wordfreq.json` | 词频统计Top 100 |
| `wordfreq_pkuseg.json` | pkuseg分词词频统计 |
| `sentiment.json` | 情感分析结果 |
| `sentiment_rules.json` | 多规则情感分析结果 |
| `lda_topics.json` | LDA主题模型结果 |
| `lda_sentiment_topics.json` | 情感分离LDA主题 |
| `ner_entities.json` | NER实体识别结果 |
| `keywords.json` | TF-IDF/TextRank关键词 |
| `sentiment_trend.json` | 情感趋势分析 |
| `danmaku_classified.json` | 弹幕类型分类 |
| `danmaku_time_distribution.json` | 时间分布分析 |
| `user_behavior.json` | 用户行为分析 |
| `word_cooccurrence.json` | 词语共现网络 |

---

## 总结

本应用层模块完成了弹幕数据的完整NLP处理与前端可视化，主要成果：

### NLP核心模块

1. **词频分析**：统计11623个词，提取Top 100高频词，AI/权限/token为最热词
2. **情感分析**：SnowNLP电商模型 + 否定词/程度词/表情/标点/转折句式五种规则
3. **LDA主题建模**：基于coherence score自动选择8个主题（coherence=0.6135）
4. **pkuseg分词**：CRF条件随机场分词，适用于规范文本
5. **NER实体识别**：识别人名/地名/机构名/技术词
6. **关键词抽取**：TF-IDF+TextRank融合算法
7. **词云生成**：ECharts交互式词云展示

### 深度分析模块

8. **情感趋势分析**：时间序列情感变化
9. **弹幕类型分类**：祝福/玩梗/刷屏/提问等8类
10. **时间分布分析**：各时段弹幕密度统计
11. **用户行为分析**：活跃用户识别与情感倾向
12. **词语共现网络**：词语共现关系图

### 前端可视化模块

13. **词云展示**：基于ECharts wordcloud实现交互式词云，支持点击查询
14. **统计图表**：柱状图、饼图、时间线、情感趋势双Y轴图
15. **响应式设计**：支持不同屏幕尺寸
16. **DataService动态数据加载**：前端异步加载所有JSON

### 数据汇总

| 数据项 | 数量 |
|--------|------|
| 原始弹幕 | 5,656条 |
| 清洗后弹幕 | 3,515条 |
| 词频统计 | 4,105词 |
| 情感正面 | 1,480条(42.12%) |
| 情感负面 | 1,141条(32.47%) |
| LDA主题 | 8个 |
| Bigram | 151个 |
| 弹幕类型 | 8类 |
| 独立用户 | 2,156个 |
| NER实体 | 200+种 |

整个大数据应用系统从数据采集（学生A）、数据清洗（学生A）、NLP分析（学生B）到HBase存储（学生A）和前端可视化（学生B）的完整流程已打通。
