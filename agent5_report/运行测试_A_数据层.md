# 数据层模块 — 运行与测试文档

> **学生A（数据层）**：负责 `agent1_crawler`（爬虫 + 数据清洗）与 `agent3_storage`（HBase 存储 + MapReduce 词频统计）两大模块的运行与测试。
>
> 本文档为**实操 runbook**，逐步指导如何在本地完成端到端的数据通道验证。

---

## 目录

1. [环境准备](#1-环境准备)
2. [模块与文件清单](#2-模块与文件清单)
3. [功能 1：B 站视频信息 + 弹幕爬取](#3-功能-1b-站视频信息--弹幕爬取)
4. [功能 2：弹幕数据清洗](#4-功能-2弹幕数据清洗)
5. [功能 3：HBase 写入（happybase 真实模式）](#5-功能-3hbase-写入happybase-真实模式)
6. [功能 4：HBase 模拟器（无 HBase 环境）](#6-功能-4hbase-模拟器无-hbase-环境)
7. [功能 5：HBase 时间范围查询](#7-功能-5hbase-时间范围查询)
8. [功能 6：MapReduce 词频统计](#8-功能-6mapreduce-词频统计)
9. [端到端联调测试](#9-端到端联调测试)
10. [常见问题排查](#10-常见问题排查)

---

## 1. 环境准备

### 1.1 操作系统
- Windows 10/11、macOS、Linux 均可
- 案例项目在 Windows 11 下开发与验证

### 1.2 Python 版本
- **Python 3.7+**（推荐 3.8/3.9，已在 Python 3.8 上验证）

```bash
python --version   # 应显示 Python 3.7.x 或更高
```

### 1.3 基础依赖

```bash
# 进入项目根目录
cd "F:\Claude Project\大数据应用系统开发实践"

# 爬虫依赖
pip install -r agent1_crawler/requirements.txt
# 等价于：pip install requests>=2.28.0

# HBase 客户端依赖（若使用真实 HBase 模式）
pip install happybase thrift
```

### 1.4 可选：HBase 环境

若没有 HBase 集群，可使用项目自带的 `hbase_simulator.py` 在内存中模拟，**不影响功能验证**。完整环境请参考 [agent3_storage/HBASE_SCHEMA.md](agent3_storage/HBASE_SCHEMA.md) 与 [agent3_storage/README.md](agent3_storage/README.md)。

真实 HBase 启动（仅供有 Hadoop 环境的同学）：

```bash
start-dfs.sh
start-hbase.sh
hbase shell
create_namespace 'bilibili'
create 'video_info',     'info', 'stats'
create 'danmaku_data',    'content', 'meta'
create 'wordfreq_data',   'stats'
```

### 1.5 B 站 Cookie

爬虫完整数据需有效 SESSDATA Cookie。无 Cookie 时仅能获取公开部分（约 1200 条），但**所有功能均可运行测试**。

获取方式：
1. 登录 [B 站](https://www.bilibili.com)
2. F12 → Network → 找到 `www.bilibili.com` 请求
3. 复制请求头中的完整 Cookie 字段
4. 粘贴到 [agent1_crawler/bilibili_crawler_v3.py:23](agent1_crawler/bilibili_crawler_v3.py#L23) 的 `COOKIE` 变量

---

## 2. 模块与文件清单

| 文件 | 作用 | 必跑 |
|------|------|------|
| `agent1_crawler/bilibili_crawler_v3.py` | B 站 API 爬虫（视频信息 + Protobuf 弹幕 + XML 备用） | ✅ |
| `agent2_nlp/clean_danmaku.py` | 弹幕清洗（特殊字符、纯数字/纯符号、繁简转换、去重） | ✅ |
| `agent3_storage/hbase_writer.py` | 写入 HBase 三张表（视频信息/弹幕/词频） | ⭕ 真实模式 |
| `agent3_storage/hbase_simulator.py` | 内存模拟 HBase 写入/查询（无需 HBase） | ✅ 起步 |
| `agent3_storage/hbase_query.py` | HBase 时间范围查询 | ⭕ 真实模式 |
| `agent3_storage/wordfreq_mapreduce.py` | MapReduce 词频统计 | ⭕ 真实模式 |
| `agent1_crawler/bilibili_data.json` | 爬虫输出（视频信息 + 原始弹幕） | 产物 |
| `agent2_nlp/cleaned_danmaku.json` | 清洗后弹幕 | 产物 |

> **实操建议**：第一次跑通时只用 `bilibili_crawler_v3.py` + `clean_danmaku.py` + `hbase_simulator.py`，三者即可完成完整数据通道验证，不依赖 HBase。

---

## 3. 功能 1：B 站视频信息 + 弹幕爬取

### 3.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\agent1_crawler"
python bilibili_crawler_v3.py
```

### 3.2 预期输出

成功时屏幕打印（与 [报告A 4.2.1 节](../agent5_report/报告A_数据层.md) 一致）：

```
============================================================
B站弹幕爬虫 - 重构版
============================================================
[1/4] 获取视频信息...
    标题: 一个视频搞懂OpenClaw！
    播放量: 5,181,106
    弹幕数(官方): 5,432
    评论数: 9,918
[2/4] Protobuf API获取弹幕...
    分片1: +3317条
    分片2: +1150条
    小计: 4467条
[3/4] XML API获取弹幕(备用)...
    获取: 1200条
[4/4] 合并去重...
    去重后: 5656条弹幕
    完整度: 5656/5432 = 104.1%
```

> 无 Cookie 时 `Protobuf API` 部分会失败或返回 0 条，仅 `XML API` 拿到约 1200 条；流程不会中断。

### 3.3 产物检查

- **生成文件**：`agent1_crawler/bilibili_data.json`（约 1.3 MB）
- **结构**：
  ```json
  {
    "video_info": {
      "bvid": "BV1jEAaz3E6K",
      "title": "一个视频搞懂OpenClaw！",
      "cid": <number>, "aid": <number>,
      "view_count": 5181106, "danmaku_count": 5432,
      "owner": { "mid": <number>, "name": "林亦LYi" }
    },
    "danmaku_list": [
      { "dmid": <number>, "content": "哈哈笑死", "timestamp": 6.123, "type": 1, "color_hex": "#ffffff" }
    ]
  }
  ```

### 3.4 测试用例

| 测试项 | 预期 | 实际 | 通过条件 |
|--------|------|------|---------|
| 视频信息获取 | 返回 title/播放量/UP主 | 5,181,106 播放 | `data["stat"]["view"] > 5_000_000` |
| Protobuf 解析 | 分片 1+2 累计 ≥ 4000 条 | 4467 条 | 数量 > 0 |
| XML 备用获取 | 拿到 1000~1300 条 | 1200 条 | 数量在 [800, 1500] |
| 合并去重 | dmid 唯一 | 唯一数=5656 | `len(set(dm["dmid"] for dm in list)) == len(list)` |
| JSON 持久化 | 1~2 MB 文件 | 1.3 MB | 文件大小 > 1 MB |
| 无 Cookie 降级 | 流程不中断 | 仅 XML 部分成功 | 仍能生成有效 JSON |

### 3.5 自检脚本

```bash
# 查看 JSON 前 30 行
head -30 agent1_crawler/bilibili_data.json

# 弹幕数量
python -c "import json; d=json.load(open('agent1_crawler/bilibili_data.json',encoding='utf-8')); print('danmaku:', len(d['danmaku_list']))"

# 唯一 dmid 数量
python -c "import json; d=json.load(open('agent1_crawler/bilibili_data.json',encoding='utf-8')); ids=[dm['dmid'] for dm in d['danmaku_list']]; print('unique:', len(set(ids)), 'total:', len(ids))"
```

---

## 4. 功能 2：弹幕数据清洗

### 4.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\agent2_nlp"
python clean_danmaku.py
```

### 4.2 预期输出

```
============================================================
弹幕数据清洗模块
============================================================
加载停用词: 743 个
读取原始弹幕: 5656 条

清洗中...
  去除特殊字符/Emoji: 253 条
  去除纯数字弹幕:    69 条
  去除纯符号弹幕:    997 条
  去除超短弹幕(<2):  51 条
  内容去重:           1013 条

清洗完成:
  输入: 5656 条
  输出: 3515 条
  保留率: 62.1%
```

### 4.3 产物检查

- **生成文件**：`agent2_nlp/cleaned_danmaku.json`
- **结构**：
  ```json
  {
    "danmaku_list": [
      { "content": "弹幕文本", "timestamp": 6.123 }
    ]
  }
  ```

### 4.4 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 输入读取 | 加载 5656 条原始弹幕 | `原始条数 == 5656` |
| 特殊字符过滤 | 去除 emoji/特殊符号 | 过滤数 ≈ 200~300 |
| 纯数字/纯符号 | 去除无效弹幕 | 过滤数 ≈ 1000 |
| 繁简转换 | 字典内繁体被替换 | 出现"网/电/语"等简体 |
| 内容去重 | 重复内容不出现 | `len(set(c)) == len(c)` |
| 输出条数 | 3000~4000 条 | 数量在 [3000, 4000] |
| JSON 合法 | 可被 `json.load` 加载 | 不抛异常 |

### 4.5 自检脚本

```bash
# 清洗后条数
python -c "import json; d=json.load(open('agent2_nlp/cleaned_danmaku.json',encoding='utf-8')); print('cleaned:', len(d['danmaku_list']))"

# 验证无空内容/纯空白
python -c "import json; d=json.load(open('agent2_nlp/cleaned_danmaku.json',encoding='utf-8')); bad=[x for x in d['danmaku_list'] if not x['content'].strip()]; print('empty:', len(bad))"
```

### 4.6 跨模块数据契约

**重要**：清洗后的 `cleaned_danmaku.json` 是后续 NLP 与 HBase 模块的输入契约，结构必须保持一致：

```json
{ "content": str, "timestamp": float }
```

任何修改都要同步通知学生 B，避免破坏下游模块。

---

## 5. 功能 3：HBase 写入（happybase 真实模式）

> 本节要求本机或远程有运行中的 HBase。若无 HBase，请直接跳到 [§6 模拟器](#6-功能-4hbase-模拟器无-hbase-环境)。

### 5.1 前置确认

```bash
# 1. HBase 进程已启动
jps    # 应看到 HMaster / HRegionServer

# 2. 表已创建
hbase shell
> list   # 应包含 video_info / danmaku_data / wordfreq_data
> exit
```

### 5.2 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\agent3_storage"

# 写入视频信息
python hbase_writer.py --mode video --input ../agent1_crawler/bilibili_data.json

# 写入清洗后弹幕
python hbase_writer.py --mode danmaku --input ../agent2_nlp/cleaned_danmaku.json

# 写入词频统计（来自 NLP 输出）
python hbase_writer.py --mode wordfreq --input ../agent2_nlp/wordfreq.json
```

### 5.3 预期输出

```
[HBase] 成功连接到 localhost:9090
[Video] 写入 1 条视频信息: BV1jEAaz3E6K
[Danmaku] 批量写入 3515 条弹幕 ...
  进度: 1000/3515
  进度: 2000/3515
  进度: 3000/3515
[Danmaku] 写入完成, 用时 3.2s
[Wordfreq] 写入 100 个高频词
全部写入完成 ✓
```

### 5.4 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| HBase 连接 | 成功 | 无 Thrift 异常 |
| 视频表写入 | 1 行 | `count 'video_info'` = 1 |
| 弹幕表写入 | 3515 行 | `count 'danmaku_data'` ≈ 3515 |
| 词频表写入 | 100+ 行 | `count 'wordfreq_data'` ≥ 100 |
| RowKey 设计 | 时间戳 8 位 | 前缀 `BV1jEAaz3E6K_00000064_*` |

---

## 6. 功能 4：HBase 模拟器（无 HBase 环境）

> **推荐起步**先用模拟器跑通数据通道，再视情况接真实 HBase。

### 6.1 一键运行

```bash
cd "F:\Claude Project\大数据应用系统开发实践\agent3_storage"

# Demo 模式：自带示例数据
python hbase_simulator.py --mode demo

# Test 模式：使用真实清洗数据
python hbase_simulator.py --mode test --input ../agent2_nlp/cleaned_danmaku.json
```

### 6.2 预期输出

```
============================================================
HBase 模拟器 - Demo 模式
============================================================
[Init] 创建模拟表: video_info
[Init] 创建模拟表: danmaku_data
[Init] 创建模拟表: wordfreq_data
[Write] 视频信息: BV1jEAaz3E6K
[Write] 弹幕数据: 3515 条
[Read]  时间范围查询 [0.0s, 60.0s]
[Result] 返回 87 条弹幕
============================================================
✓ 模拟器测试通过
```

### 6.3 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 表创建 | 3 张表 | 模拟器内部维护 3 个 dict |
| 写入 | 3515 条弹幕 | 计数器 = 3515 |
| 时间范围查询 | 返回 0~60s 弹幕 | 数量在 [50, 200] |
| 查询返回结构 | 含 rowkey/content/timestamp | 字段齐全 |

### 6.4 自检脚本

```python
# Python 内联验证
import sys
sys.path.insert(0, 'agent3_storage')
from hbase_simulator import HBaseSimulator

sim = HBaseSimulator()
print('Tables:', list(sim.tables.keys()))     # ['video_info','danmaku_data','wordfreq_data']
sim.write_danmaku('BV1', [{'dmid':1, 'content':'hi', 'timestamp':10.0, 'color_hex':'#fff'}])
print('Danmaku count:', len(sim.tables['danmaku_data']))  # 1
print('Range query:', sim.query_danmaku_by_timerange('BV1', 0, 100))  # 1 条
```

---

## 7. 功能 5：HBase 时间范围查询

### 7.1 真实 HBase 模式

```bash
cd "F:\Claude Project\大数据应用系统开发实践\agent3_storage"
python hbase_query.py --bv BV1jEAaz3E6K --start 0 --end 60
```

### 7.2 模拟器模式

```bash
python hbase_query.py --mode sim --bv BV1jEAaz3E6K --start 0 --end 60
```

### 7.3 预期输出

```
查询弹幕: BV1jEAaz3E6K, 时间范围 [0s, 60s]
返回 87 条:
  [00:06] 哈哈笑死
  [00:39] 小龙虾来了
  [00:58] 为什么要叫这个名字
  ...
```

### 7.4 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 0~60s 范围 | 80~150 条 | 数量在 [80, 150] |
| 完整 0~end | 3515 条 | 数量 = 清洗后条数 |
| 字段完整性 | 包含 content/timestamp/rowkey | 字段齐全 |

---

## 8. 功能 6：MapReduce 词频统计

### 8.1 本地模式（无需 Hadoop）

```bash
cd "F:\Claude Project\大数据应用系统开发实践\agent3_storage"
python wordfreq_mapreduce.py --mode local --input ../agent2_nlp/cleaned_danmaku.json
```

### 8.2 预期输出

```
[MapReduce] Local 模式启动
[Map]    分词中（jieba）...
[Map]    完成 3515 条弹幕分词
[Shuffle] 聚合相同 word...
[Reduce]  输出 Top 100 词频
[Result]  AI: 142, 权限: 87, 模型: 76, token: 65, ...
[Write]   保存到 ../agent2_nlp/wordfreq_mapreduce.json
```

### 8.3 Hadoop 集群模式（可选）

```bash
# 提交到 Hadoop 集群
hadoop jar wordfreq_mapreduce.jar \
    -input hdfs://namenode:9000/bilibili/danmaku \
    -output hdfs://namenode:9000/bilibili/wordfreq
```

### 8.4 测试用例

| 测试项 | 预期 | 通过条件 |
|--------|------|---------|
| 分词 Mapper | 输出 (word, 1) | 迭代器非空 |
| 聚合 Reducer | 同一 word 求和 | 与 `nlp_process.py` 结果一致 |
| Top 100 输出 | 高频词排序 | 数量 = 100 |

---

## 9. 端到端联调测试

> **目标**：从 B 站 API 一次跑到 HBase 落库，验证全链路。

### 9.1 测试脚本

将以下命令保存为 `agent5_report/run_e2e_A.sh`（或逐行复制）：

```bash
#!/bin/bash
set -e
ROOT="F:\Claude Project\大数据应用系统开发实践"

echo "==== 1. 爬虫采集 ===="
cd "$ROOT/agent1_crawler"
python bilibili_crawler_v3.py

echo "==== 2. 数据清洗 ===="
cd "$ROOT/agent2_nlp"
python clean_danmaku.py

echo "==== 3. HBase 模拟器测试 ===="
cd "$ROOT/agent3_storage"
python hbase_simulator.py --mode test --input ../agent2_nlp/cleaned_danmaku.json

echo "==== 4. MapReduce 词频统计 ===="
python wordfreq_mapreduce.py --mode local --input ../agent2_nlp/cleaned_danmaku.json

echo "==== 全部完成 ✓ ===="
```

### 9.2 一键执行

```bash
cd "F:\Claude Project\大数据应用系统开发实践"
bash agent5_report/run_e2e_A.sh
```

### 9.3 联调通过标准

| 阶段 | 关键产物 | 通过条件 |
|------|---------|---------|
| 爬虫 | `agent1_crawler/bilibili_data.json` | 存在 + 包含 video_info 与 danmaku_list |
| 清洗 | `agent2_nlp/cleaned_danmaku.json` | 存在 + danmaku_list 长度 3000~4000 |
| HBase 模拟 | 模拟器返回非空结果 | 写入 3515 条 + 范围查询有数据 |
| MapReduce | `wordfreq_mapreduce.json` | 存在 + Top 100 不为空 |

### 9.4 联调失败排查顺序

1. **爬虫返回 0 条** → 检查 Cookie；无 Cookie 至少能拿到 XML 部分
2. **清洗文件找不到** → 先确认上一步 `bilibili_data.json` 已生成
3. **HBase 连接失败** → 改用 `hbase_simulator.py` 验证后续逻辑
4. **MapReduce jieba 报错** → 单独 `pip install jieba`，确认 `cn_stopwords.txt` 在 `agent2_nlp/`

---

## 10. 常见问题排查

### Q1. 爬虫一直返回 0 条弹幕

- **原因**：未配置 SESSDATA Cookie，B 站 WBI 签名拦截
- **解决**：参考 [§1.5](#15-b-站-cookie) 配置 Cookie；或接受无 Cookie 模式（仅 XML 备用 1200 条）

### Q2. `bilibili_crawler_v3.py` 报 `JSON decode error`

- **原因**：HTTP 429 被风控
- **解决**：在脚本中调大 `time.sleep()` 间隔；或更换 IP

### Q3. `clean_danmaku.py` 找不到 `bilibili_data.json`

- **原因**：路径 BASE_DIR 硬编码为开发机路径
- **解决**：在 `clean_danmaku.py` 顶部修改 `BASE_DIR` 为本机项目根目录

### Q4. HBase Thrift 报 `TTransportException`

- **原因**：HBase Thrift 服务未启动
- **解决**：
  ```bash
  hbase-daemon.sh start thrift
  # 或
  hbase-daemon.sh start thrift -p 9090
  ```

### Q5. `wordfreq_mapreduce.py` 内存溢出

- **原因**：弹幕量超过 10 万条时本地模式内存不足
- **解决**：减少测试数据；或提交到 Hadoop 集群运行

### Q6. 模拟器通过但真实 HBase 失败

- **原因**：表结构或列族未创建
- **解决**：执行 §1.4 中的 `create '...'` 语句

---

## 附录：相关文件路径速查

| 文件 | 路径 |
|------|------|
| 爬虫主程序 | [agent1_crawler/bilibili_crawler_v3.py](../agent1_crawler/bilibili_crawler_v3.py) |
| 清洗模块 | [agent2_nlp/clean_danmaku.py](../agent2_nlp/clean_danmaku.py) |
| 停用词表 | [agent2_nlp/cn_stopwords.txt](../agent2_nlp/cn_stopwords.txt) |
| HBase 写入 | [agent3_storage/hbase_writer.py](../agent3_storage/hbase_writer.py) |
| HBase 查询 | [agent3_storage/hbase_query.py](../agent3_storage/hbase_query.py) |
| HBase 模拟器 | [agent3_storage/hbase_simulator.py](../agent3_storage/hbase_simulator.py) |
| MapReduce 词频 | [agent3_storage/wordfreq_mapreduce.py](../agent3_storage/wordfreq_mapreduce.py) |
| HBase 表结构 | [agent3_storage/HBASE_SCHEMA.md](../agent3_storage/HBASE_SCHEMA.md) |
| 存储设计文档 | [agent3_storage/README.md](../agent3_storage/README.md) |
| 课程设计报告 | [报告A_数据层.md](报告A_数据层.md) |
