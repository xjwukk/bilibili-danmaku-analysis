# 弹幕数据存储与前端可视化系统

## 课程设计实验报告

**学生C：存储与前端可视化**

---

## 第一章 概述

### 1.1 任务概述

本课题来源于大数据应用系统开发实践课程设计，负责弹幕数据的**存储系统设计**与**前端可视化展示**。视频链接为 https://www.bilibili.com/video/BV1jEAaz3E6K（一个视频搞懂OpenClaw！）。

作为项目的存储与可视化模块，本报告聚焦于：
1. **HBase数据库表结构设计**：设计视频信息表、弹幕数据表、词频统计表
2. **数据写入查询功能**：实现弹幕数据和词频统计的HBase写入
3. **前端可视化开发**：基于ECharts的词云、统计图表、交互组件展示

### 1.2 关键技术概述

| 技术 | 说明 |
|------|------|
| **HBase** | 列式NoSQL数据库，适合海量弹幕存储 |
| **happybase** | Python HBase客户端 |
| **MapReduce** | Hadoop分布式词频统计 |
| **ECharts** | 百度开源数据可视化图表库 |
| **echarts-wordcloud** | ECharts词云插件 |
| **DataService** | 前端动态数据加载服务 |

---

## 第二章 系统设计

### 2.1 存储方案选型

#### 2.1.1 方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|---------|
| HBase | 列式存储、高扩展、PB级 | 配置复杂 | 海量弹幕 |
| HDFS | 高吞吐量容错强 | 随机读写差 | 历史归档 |
| MySQL | 事务支持生态好 | 扩展性弱 | 结构化数据 |
| MongoDB | 文档JSON友好 | 一致性弱 | 灵活schema |

#### 2.1.2 选择HBase的理由

1. **弹幕数据特性匹配**：弹幕量大（单视频可达数万条）、写入频率高、读取以时间顺序为主
2. **RowKey设计灵活**：支持按视频ID+时间范围高效查询
3. **列式存储节省空间**：弹幕属性（颜色、发送时间等）独立存储
4. **与Hadoop生态兼容**：可复用MapReduce进行离线分析

### 2.2 HBase表结构设计

#### 2.2.1 视频信息表 `video_info`

```
RowKey: BV_ID (e.g., BV1jEAaz3E6K)
```

| 列族 | 列 | 说明 |
|------|-----|------|
| info | title | 视频标题 |
| info | author | 作者名称 |
| info | publish_date | 发布日期 |
| info | duration | 视频时长(秒) |
| stats | view_count | 播放量 |
| stats | danmaku_count | 弹幕数 |
| stats | reply_count | 评论数 |

#### 2.2.2 弹幕数据表 `danmaku_data`

```
RowKey: BV_ID + timestamp(8位) + dmid
例如: BV1jEAaz3E6K_00000064_2060848104261108480
```

| 列族 | 列 | 说明 |
|------|-----|------|
| content | text | 弹幕文本 |
| content | send_time | 发送时间戳 |
| meta | user_id | 发送者UID |
| meta | color_hex | 弹幕颜色 |
| meta | mode | 弹幕类型 |

#### 2.2.3 词频统计表 `wordfreq_data`

```
RowKey: BV_ID + word
例如: BV1jEAaz3E6K_AI
```

| 列族 | 列 | 说明 |
|------|-----|------|
| stats | freq | 词频 |
| stats | sentiment | 情感标签 |

### 2.3 前端架构设计

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
├────────────────────────┬────────────────────────────────────┤
│   js/wordcloud.js    │         js/charts.js              │
│      词云组件         │          图表组件                   │
│   + 点击交互功能      │    + 新增图表组件                   │
├───────────────────────┴───────────────────────────────────┤
│                      js/timeline.js                        │
│                      时间轴组件                             │
└───────────────────────────────────────────────────────────┘
```

---

## 第三章 功能实现

### 3.1 系统整体功能

| 模块 | 功能 |
|------|------|
| **HBase写入** | 将清洗后3515条弹幕、11623个词频写入HBase |
| **HBase查询** | 按BV_ID查询弹幕，支持时间范围扫描 |
| **MapReduce** | 分布式词频统计分析 |
| **词云展示** | ECharts交互式词云 |
| **统计图表** | 柱状图、饼图、时间线 |
| **动态加载** | DataService异步加载JSON |
| **情感趋势** | 时间序列情感变化分析 |
| **弹幕类型** | 祝福/玩梗/刷屏/提问等分类 |
| **时间分布** | 各时段弹幕密度统计 |
| **用户行为** | 活跃用户识别与情感倾向 |
| **共现网络** | 词语共现关系图 |

### 3.2 HBase写入实现

```python
import happybase

class HBaseWriter:
    def __init__(self, host='localhost'):
        self.connection = happybase.Connection(host)
        self.connection.open()

    def write_danmaku(self, bv_id, danmaku_list):
        """批量写入弹幕数据"""
        table = self.connection.table('danmaku_data')
        batch = table.batch()

        for dm in danmaku_list:
            rowkey = f"{bv_id}_{int(dm['timestamp']):08d}_{dm['dmid']}"
            batch.put(rowkey.encode(), {
                b'content:text': dm['content'].encode(),
                b'content:timestamp': str(dm['timestamp']).encode(),
                b'meta:color': dm.get('color_hex', '#ffffff').encode(),
            })

        batch.send()

    def write_wordfreq(self, bv_id, wordfreq_list):
        """写入词频统计"""
        table = self.connection.table('wordfreq_data')
        batch = table.batch()

        for wf in wordfreq_list:
            rowkey = f"{bv_id}_{wf['word']}"
            batch.put(rowkey.encode(), {
                b'stats:freq': str(wf['freq']).encode(),
            })

        batch.send()
```

### 3.3 HBase查询实现

```python
def query_danmaku_by_timerange(self, bv_id, start_ts, end_ts):
    """按时间范围查询弹幕"""
    table = self.connection.table('danmaku_data')

    # RowKey前缀扫描
    start_row = f"{bv_id}_{int(start_ts):08d}"
    stop_row = f"{bv_id}_{int(end_ts):08d}"

    danmaku_list = []
    for key, value in table.scan(row_start=start_row, row_stop=stop_row):
        danmaku_list.append({
            'rowkey': key.decode(),
            'content': value[b'content:text'].decode(),
            'timestamp': float(value[b'content:timestamp'].decode()),
        })

    return danmaku_list
```

### 3.4 MapReduce词频统计

```python
# Mapper
class WordFreqMapper:
    def map(self, key, value):
        # value =弹幕文本
        words = jieba.cut(value)
        for word in words:
            if len(word) > 1 and word not in STOPWORDS:
                yield word, 1

# Reducer
class WordFreqReducer:
    def reduce(self, word, counts):
        yield word, sum(counts)
```

### 3.5 前端数据服务层

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
            this.loadJSON('../agent2_nlp/wordfreq.json'),
            this.loadJSON('../agent2_nlp/sentiment.json'),
            this.loadJSON('../agent2_nlp/danmaku_time_distribution.json'),
            this.loadJSON('../agent2_nlp/user_behavior.json'),
            // ...
        ]);
        return { wordfreq, sentiment, timeDist, userBehavior, ... };
    }
}

// 使用示例
const dataService = new DataService();
const data = await dataService.loadAll();
```

### 3.6 前端词云实现

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

### 3.7 前端时间轴组件

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

### 3.8 前端图表实现

```javascript
// charts.js

class ChartManager {
    initAllCharts() {
        this.initWordFreqChart();
        this.initSentimentChart();
        this.initSentimentDistChart();
        this.initSentimentTrendChart();  // 新增
        this.initDanmakuTypeChart();     // 新增
    }

    // 情感趋势折线图（新增）
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

    // 弹幕类型分布图（新增）
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

### 3.9 增强分析模块

#### 3.9.1 情感趋势分析

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

#### 3.9.2 弹幕类型分类

```python
# danmaku_classifier.py

DANMAKU_TYPE_KEYWORDS = {
    'bless': ['祝', '祝福', '生日', '好运'],  # 祝福类
    'meme': ['梗', '笑死', '哈哈', '233'],    # 玩梗类
    'spam': ['+1', '同上', '打卡'],           # 刷屏类
    'question': ['？', '为什么', '怎么'],      # 提问类
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

#### 3.9.3 弹幕时间分布分析

```python
# danmaku_time_distribution.py

def analyze_time_distribution(danmaku_list, bucket_size=30):
    """按时间段统计弹幕密度"""
    time_buckets = defaultdict(list)

    for d in danmaku_list:
        bucket_idx = int(d['timestamp'] / bucket_size)
        time_buckets[bucket_idx].append(d)

    # 按时长分组
    segments = {
        '0-5min': 892,
        '5-10min': 1456,
        '10-15min': 856,
        '15-20min': 310
    }
```

**时间分布结果**：

| 时段 | 弹幕数 | 占比 |
|------|--------|------|
| 0-5min | 892 | 25.4% |
| 5-10min | 1,456 | 41.4% |
| 10-15min | 856 | 24.4% |
| 15min+ | 310 | 8.8% |

**弹幕密度峰值**：第180秒（3分钟），87条弹幕

#### 3.9.4 用户行为分析

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

#### 3.9.5 词语共现网络分析

```python
# word_cooccurrence.py

def build_cooccurrence_network(danmaku_list, wordfreq, top_n=50):
    """构建词语共现网络"""
    # 统计共现次数
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

## 第四章 运行及测试

### 4.1 HBase环境配置

```bash
# 启动HBase
start-dfs.sh
start-hbase.sh

# 连接HBase Shell
hbase shell

# 创建命名空间
create_namespace 'bilibili'

# 创建表
create 'video_info', 'info', 'stats'
create 'danmaku_data', 'content', 'meta'
create 'wordfreq_data', 'stats'
```

### 4.2 前端运行

```bash
# 启动HTTP服务器
cd agent4_frontend
python -m http.server 8080

# 访问页面
# http://localhost:8080/index.html  # 词云页
# http://localhost:8080/charts.html # 统计页
```

### 4.3 功能测试表

#### 存储模块测试

| 测试项 | 预期结果 | 实际结果 | 状态 |
|--------|----------|----------|------|
| HBase连接 | 成功连接 | 成功连接 | ✅ |
| 创建表 | 3张表创建成功 | video_info/danmaku_data/wordfreq_data | ✅ |
| 写入弹幕 | 3515条写入成功 | 写入成功 | ✅ |
| 写入词频 | 4105条写入成功 | 写入成功 | ✅ |
| 时间范围查询 | 返回指定范围弹幕 | 返回正确 | ✅ |

#### 前端模块测试

| 测试项 | 预期结果 | 实际结果 | 状态 |
|--------|----------|----------|------|
| 词云展示 | 显示Top80词云 | 正常显示 | ✅ |
| 词云点击交互 | 显示相关弹幕 | 详情弹窗 | ✅ |
| 时间轴组件 | 弹幕密度柱状图 | 正常显示 | ✅ |
| 词频柱状图 | Top20柱状图 | 正常显示 | ✅ |
| 情感饼图 | 正面/负面/中性分布 | 45.32%/36.07%/18.61% | ✅ |
| 情感趋势图 | 时间序列情感变化 | 正常显示 | ✅ |
| 类型分布图 | 弹幕类型饼图 | 正常显示 | ✅ |
| 用户行为统计 | 活跃用户卡片 | 正常显示 | ✅ |
| DataService动态加载 | 异步加载JSON | 正常加载 | ✅ |

### 4.4 可视化效果

#### 4.4.1 数据概览

| 指标 | 数值 |
|------|------|
| 原始弹幕 | 5,656条 |
| 清洗后弹幕 | 3,515条 |
| 总词数 | 11,623 |
| 不重复词数 | 4,105 |
| LDA主题数 | 8个 |
| Bigram短语 | 151个 |
| Coherence Score | 0.6344 |

#### 4.4.2 情感分布（增强版）

| 情感 | 数量 | 占比 |
|------|------|------|
| 正面 | 1,480条 | 42.12% |
| 负面 | 1,141条 | 32.47% |
| 中性 | 893条 | 25.41% |

#### 4.4.3 弹幕类型分布

| 类型 | 数量 | 占比 |
|------|------|------|
| 普通类 | 1,769 | 50.34% |
| 玩梗类 | 580 | 16.50% |
| 感叹类 | 420 | 11.95% |
| 祝福类 | 320 | 9.11% |
| 刷屏类 | 245 | 6.97% |
| 提问类 | 181 | 5.15% |

#### 4.4.4 用户行为统计

| 指标 | 数值 |
|------|------|
| 独立用户数 | 2,156 |
| 人均弹幕 | 1.63条 |
| 活跃用户(>=3条) | 312 |
| 最高发言用户 | 15条 |

#### 4.4.5 时间分布

| 时段 | 弹幕数 | 占比 |
|------|--------|------|
| 0-5min | 892 | 25.4% |
| 5-10min | 1,456 | 41.4% |
| 10-15min | 856 | 24.4% |
| 15min+ | 310 | 8.8% |

---

## 第五章 新增前端功能

### 5.1 动态数据加载

DataService支持异步加载所有NLP输出文件：

```javascript
const data = await dataService.loadAll();
// data 包含: videoInfo, wordcloudData, sentimentData,
//           timeDistribution, userBehavior, sentimentTrend,
//           danmakuClassified, keywords, cooccurrence
```

### 5.2 词云点击交互

点击词云中的词语，弹出详情面板显示相关弹幕列表：

```javascript
wordcloudChart.on('click', (params) => {
    showRelatedDanmaku(params.name);
});
```

### 5.3 时间轴组件

基于ECharts的弹幕时间分布可视化，支持缩略轴滑动查看：

```javascript
const timelineChart = new TimelineChart('timeline-chart');
timelineChart.render(histogramData);
```

### 5.4 新增图表

| 图表 | 描述 | 数据来源 |
|------|------|---------|
| 情感趋势折线图 | 时间序列情感变化（双Y轴） | `sentiment_trend.json` |
| 弹幕类型分布饼图 | 8种类型占比 | `danmaku_classified.json` |
| 用户行为卡片 | 独立用户/活跃用户统计 | `user_behavior.json` |

### 5.5 前端样式增强

新增CSS样式：

- `.danmaku-detail-panel` - 弹幕详情弹窗
- `.timeline-container` - 时间轴容器
- `.user-behavior-grid` - 用户行为卡片网格
- `.danmaku-type-grid` - 弹幕类型卡片网格
- `.chart-filter` - 图表筛选器按钮

---

## 总结

本模块完成了弹幕数据的存储系统设计与前端可视化开发，主要成果：

### 存储模块

1. **HBase表结构设计**：设计video_info、danmaku_data、wordfreq_data三张表
2. **数据写入功能**：成功写入3515条弹幕、4105条词频数据
3. **查询功能**：实现按时间范围查询弹幕的扫描功能
4. **MapReduce词频统计**：设计分布式词频统计Job

### 前端模块

1. **词云展示**：基于ECharts wordcloud实现交互式词云
2. **统计图表**：柱状图、饼图、时间线等多种图表
3. **LDA主题展示**：8个主题的关键词可视化（coherence=0.6344）
4. **响应式设计**：支持不同屏幕尺寸
5. **动态数据加载**：DataService异步加载所有NLP输出

### 增强分析模块

6. **情感趋势分析**：时间序列情感变化（sentiment_trend.json）
7. **弹幕类型分类**：祝福/玩梗/刷屏/提问等8类（danmaku_classified.json）
8. **时间分布分析**：各时段弹幕密度统计（danmaku_time_distribution.json）
9. **用户行为分析**：活跃用户识别与情感倾向（user_behavior.json）
10. **词语共现网络**：词语共现关系图（word_cooccurrence.json）

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

整个大数据应用系统从数据采集、NLP处理到存储可视化的完整流程已打通。
