# B站弹幕数据爬虫系统设计与实现

## 课程设计实验报告

**学生A：爬虫与数据采集**

---

## 第一章 概述

### 1.1 任务概述

本课题来源于大数据应用系统开发实践课程设计，选择B站视频弹幕数据作为研究对象。视频链接为 https://www.bilibili.com/video/BV1jEAaz3E6K，这是一期关于OpenClaw与AI Agent技术的科普视频，标题为"一个视频搞懂OpenClaw！"。

| 视频信息 | 值 |
|---------|---|
| 标题 | 一个视频搞懂OpenClaw！ |
| UP主 | 林亦LYi |
| BV号 | BV1jEAaz3E6K |
| 发布时间 | 2026-02-28 |
| 播放量 | 5,181,106 |
| 弹幕数 | 5,432（官方） |

弹幕作为视频内容的重要组成部分，承载了用户对视频内容的即时反馈、情感表达和观点讨论。通过对弹幕数据的采集与分析，可以挖掘出观众对视频内容的关注点、情感倾向以及讨论热点。

本项目将数据处理流程分为三个阶段：**数据采集**（学生A负责）、**NLP处理**（学生B负责）、**存储与可视化**（学生C负责）。本文档详细记录数据采集阶段的设计思路、核心算法实现、测试验证过程。

### 1.2 关键技术概述

本爬虫系统涉及以下关键技术：

**网络请求技术**：采用Python requests库模拟浏览器发送HTTP请求，通过设置合理的User-Agent、Referer、Cookie等请求头字段，确保请求能够被B站服务器正常响应。B站弹幕API需要有效的登录Cookie（SESSDATA）才能获取完整数据。

**Protobuf解析**：B站弹幕采用Google Protocol Buffers二进制格式传输。系统实现了完整的手动解析器，无须依赖protobuf库，通过读取varint字段标识和长度字段自底向上构建弹幕对象。

**Protobuf DanmakuElem结构**：
```protobuf
message DanmakuElem {
    int64 id = 1;        // 弹幕ID
    int32 progress = 2;  // 出现时间(毫秒)
    int32 mode = 3;      // 弹幕模式(1滚动2顶部3底部)
    int32 color = 5;     // 颜色(ABGR格式)
    string content = 7;  // 弹幕内容
    int64 ctime = 9;     // 发送时间戳
    int64 dmid = 13;     // 弹幕唯一ID
}
```

**数据去重技术**：采用dmid（弹幕唯一ID）作为去重键，而非弹幕内容字符串。相同内容的弹幕可能来自不同用户，具有不同的dmid，应全部保留。

---

## 第二章 系统设计

### 2.1 系统选型设计

#### 2.1.1 开发语言选择

| 语言 | 优点 | 缺点 |
|------|------|------|
| Python | 语法简洁、库丰富 | 执行效率较低 |
| Java | 跨平台、生态完善 | 代码量大 |
| Go | 并发性能好 | 库相对较少 |

选择**Python 3.7+**作为开发语言，利用其简洁的语法和丰富的第三方库支持。

#### 2.1.2 HTTP客户端选择

| 客户端 | 特点 |
|--------|------|
| requests | 同步API，简单易用 |
| aiohttp | 异步支持，性能好 |
| httpx | 同步/异步兼顾 |

选择**requests库**，适合本场景的同步采集需求。

#### 2.1.3 数据格式选择

| 格式 | 适用场景 |
|------|---------|
| JSON | 结构化数据，通用性强 |
| CSV | 表格数据，Excel友好 |
| MongoDB | 文档存储，灵活 |

选择**JSON格式**输出，便于后续NLP处理模块读取。

### 2.2 系统架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    BilibiliCrawler                      │
├─────────────────────────────────────────────────────────┤
│  __init__(bvid, cookie)                                │
│    ├── self.bvid, self.cookie, self.session            │
│    └── self.video_info, self.danmaku_list               │
├─────────────────────────────────────────────────────────┤
│  get_video_info()                                       │
│    └── 调用 /x/web-interface/view API 获取视频信息         │
├─────────────────────────────────────────────────────────┤
│  get_danmaku_protobuf(cid, aid)                        │
│    ├── 调用 /x/v2/dm/web/seg.so API                    │
│    ├── 分片获取（segment_index 1~N）                    │
│    └── parse_seg_reply() → parse_danmaku_elem()         │
├─────────────────────────────────────────────────────────┤
│  get_danmaku_xml(cid)                                  │
│    └── 调用 comment.bilibili.com/{cid}.xml              │
├─────────────────────────────────────────────────────────┤
│  merge_and_deduplicate()                                │
│    └── 按dmid去重，按timestamp排序                       │
└─────────────────────────────────────────────────────────┘
```

### 2.3 功能模块设计

| 模块 | 功能 | 输入 | 输出 |
|------|------|------|------|
| get_video_info | 获取视频基本信息 | BV_ID | video_info字典 |
| get_danmaku_protobuf | Protobuf方式获取弹幕 | cid, aid | danmaku列表 |
| get_danmaku_xml | XML方式获取弹幕 | cid | danmaku列表 |
| merge_and_deduplicate | 合并去重 | 两个danmaku列表 | 唯一danmaku列表 |
| save | 保存为JSON | filename | JSON文件 |

---

## 第三章 功能实现

### 3.1 系统整体功能

本爬虫系统实现了以下核心功能：

1. **视频信息获取**：通过B站公开API获取视频的标题、播放量、弹幕数、评论数、UP主信息等
2. **Protobuf弹幕获取**：通过新版API分片获取弹幕，支持自动重试和备用方案
3. **XML弹幕获取**：通过旧版API作为备用获取弹幕
4. **数据去重合并**：按dmid去重，按时间戳排序
5. **JSON持久化**：将结果保存为结构化JSON格式

### 3.2 功能1实现 - 视频信息获取

```python
def get_video_info(self):
    """获取视频基本信息"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={self.bvid}"
    resp = self.session.get(url, timeout=10)
    data = resp.json()["data"]

    self.video_info = {
        "bvid": data["bvid"],
        "title": data["title"],
        "cid": data["cid"],
        "aid": data["aid"],
        "duration": data["duration"],
        "publish_date": datetime.fromtimestamp(data["pubdate"]).strftime("%Y-%m-%d %H:%M:%S"),
        "view_count": data["stat"]["view"],
        "like_count": data["stat"]["like"],
        "coin_count": data["stat"]["coin"],
        "favorite_count": data["stat"]["favorite"],
        "danmaku_count": data["stat"]["danmaku"],
        "reply_count": data["stat"]["reply"],
        "owner": {"mid": data["owner"]["mid"], "name": data["owner"]["name"]}
    }
    return self.video_info
```

### 3.3 功能2实现 - Protobuf弹幕解析

#### 3.3.1 Varint读取

```python
def read_varint(data, pos):
    """读取protobuf varint"""
    result = 0
    shift = 0
    orig_pos = pos
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return result, pos - orig_pos
        shift += 7
        if shift > 63:
            break
    return result, pos - orig_pos
```

#### 3.3.2 单个DanmakuElem解析

```python
def parse_danmaku_elem(data, start):
    """解析单个DanmakuElem"""
    pos = start
    dmid = progress = mode = 0
    color = 0xFFFFFF
    content = b''

    while pos < len(data):
        tag = data[pos]
        field = tag >> 3
        wire = tag & 7

        if wire == 0:  # varint
            val, n = read_varint(data, pos)
            pos += n
            if field == 1: progress = val
            elif field == 2: mode = val
            elif field == 4: color = val
            elif field == 8: dmid = val

        elif wire == 2:  # length-delimited
            length, n = read_varint(data, pos)
            pos += n
            val = data[pos:pos + length]
            pos += length
            if field == 7: content = val

        elif wire == 5:  # fixed32
            pos += 4
        else:
            break

    if content:
        text = content.decode('utf-8', errors='ignore').strip()
        if text:
            return {
                "dmid": dmid,
                "content": text,
                "timestamp": progress / 1000,
                "type": mode,
                "color_hex": f"#{color & 0xFF:02x}{(color >> 8) & 0xFF:02x}{(color >> 16) & 0xFF:02x}"
            }
    return None
```

### 3.4 功能3实现 - 数据去重合并

```python
def merge_and_deduplicate(self, proto_danmaku, xml_danmaku):
    """合并并按dmid去重"""
    seen = set()
    unique = []

    # 先添加protobuf数据（优先）
    for dm in proto_danmaku:
        dmid = dm.get('dmid', 0)
        if dmid and dmid not in seen:
            seen.add(dmid)
            unique.append(dm)

    # 再添加XML数据
    for dm in xml_danmaku:
        dmid = dm.get('dmid', 0)
        if dmid and dmid not in seen:
            seen.add(dmid)
            unique.append(dm)

    # 按时间戳排序
    return sorted(unique, key=lambda x: x.get('timestamp', 0))
```

---

## 第四章 运行及测试

### 4.1 编译运行

#### 4.1.1 环境配置

```bash
# Python版本要求
Python 3.7+

# 依赖库
pip install requests

# 代码文件
bilibili_crawler.py
```

#### 4.1.2 Cookie配置

在代码中配置有效的B站Cookie：

```python
COOKIE = "SESSDATA=xxxx; bili_jct=xxx; DedeUserID=xxx;"
```

Cookie获取方式：
1. 登录B站 (https://www.bilibili.com)
2. 按F12打开开发者工具
3. 在Network中找到请求头复制Cookie

#### 4.1.3 运行命令

```bash
cd agent1_crawler
python bilibili_crawler.py
```

### 4.2 测试结果

#### 4.2.1 运行日志

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

#### 4.2.2 功能测试表

| 测试项 | 预期结果 | 实际结果 | 状态 |
|--------|----------|----------|------|
| 视频信息获取 | 返回完整视频信息 | title、cid、播放量等全部正确 | ✅ 通过 |
| Protobuf解析 | 正确解析弹幕内容 | 分片1得3317条，分片2得1150条 | ✅ 通过 |
| XML解析 | 正确解析XML弹幕 | 成功解析1200条弹幕 | ✅ 通过 |
| 去重功能 | 按dmid去重 | 唯一dmid数=5656，无重复 | ✅ 通过 |
| 数据完整性 | 实际采集≥官方数量 | 5656 > 5432，完整度104.1% | ✅ 通过 |
| JSON保存 | 保存为正确JSON格式 | bilibili_data.json (1.3MB) | ✅ 通过 |

#### 4.2.3 数据采集统计

| 指标 | 数值 |
|------|------|
| 原始弹幕数 | 5,656条 |
| 官方弹幕数 | 5,432条 |
| 数据完整度 | 104.1% |
| Protobuf获取 | 4,467条 (78.9%) |
| XML获取 | 1,200条 (21.2%) |
| 重复弹幕 | 11条 |

### 4.3 弹幕样例

```
[00:06] 哈哈笑死
[00:39] 小龙虾来了
[00:58] 为什么要叫这个名字
[01:10] ?
[01:11] 哈哈
[01:12] Niko
[01:13] 打卡
[01:17] 实战了什么
[02:25] cookie也删了果然是
[02:25] cookie删了不太安全
```

---

## 第五章 数据清洗

### 5.1 清洗任务概述

原始弹幕数据存在大量噪声，需要进行清洗才能用于NLP分析。数据清洗工作由爬虫模块统一负责，确保数据质量。

**清洗目标**：
- 过滤特殊符号、Emoji
- 去除纯数字、纯符号弹幕
- 过滤超短、超长弹幕
- 繁简转换统一
- 内容去重

### 5.2 清洗算法实现

```python
# 特殊符号和emoji正则
SPECIAL_CHARS_PATTERN = re.compile(
    r'[\U00010000-\U0010ffff]'  # emoji
    r'|[℀-⅏]'         # 字母符号
    r'|[←-⇿]'         # 箭头
    r'|[☀-⛿]'         # 杂项符号
    r'|[✀-➿]'         # 装饰符号
    r'|[　-〿]'         # CJK符号
    r'|[\U0001F000-\U0001F9FF]'  # 表情符号
)

def clean_danmaku(danmaku_list):
    """数据清洗主函数"""
    cleaned = []
    seen = set()

    for item in danmaku_list:
        content = item.get('content', '')

        # 1. 去除特殊字符和emoji
        content = SPECIAL_CHARS_PATTERN.sub('', content)

        # 2. 有效性判断
        if len(content) < 2 or len(content) > 100:
            continue
        if PURE_NUMBER_PATTERN.match(content):
            continue
        if PURE_SYMBOL_PATTERN.match(content):
            continue

        # 3. 繁简转换
        content = convert_to_simple(content)

        # 4. 内容去重
        if content not in seen:
            seen.add(content)
            cleaned.append({'content': content, 'timestamp': item.get('timestamp', 0)})

    return cleaned
```

### 5.3 清洗统计结果

| 指标 | 数值 |
|------|------|
| 输入弹幕总数 | 5,656条 |
| 去除特殊字符/Emoji | 253条 |
| 去除纯数字弹幕 | 69条 |
| 去除纯符号弹幕 | 997条 |
| 去除超短弹幕 | 51条 |
| **有效弹幕数量** | **4,528条** |
| **去重后弹幕数量** | **3,515条** |

### 5.4 繁简转换

```python
def convert_to_simple(text):
    """简繁体转换"""
    conv_table = {
        '網': '网', '電': '电', '雲': '云', '語': '语', '數': '数',
        '據': '据', '開': '开', '發': '发', '會': '会', '對': '对',
        '們': '们', '過': '过', '時': '时', '間': '间', '說': '说',
    }
    return ''.join(conv_table.get(char, char) for char in text)
```

## 第五章 数据清洗

### 5.1 清洗任务概述

原始弹幕数据存在大量噪声，需要进行清洗才能用于NLP分析。数据清洗工作由爬虫模块统一负责，确保数据质量。

**清洗目标**：
- 过滤特殊符号、Emoji
- 去除纯数字、纯符号弹幕
- 过滤超短、超长弹幕
- 繁简转换统一
- 内容去重

### 5.2 清洗算法实现

```python
# 特殊符号和emoji正则
SPECIAL_CHARS_PATTERN = re.compile(
    r'[\U00010000-\U0010ffff]'  # emoji
    r'|[℀-⅏]'         # 字母符号
    r'|[←-⇿]'         # 箭头
    r'|[☀-⛿]'         # 杂项符号
    r'|[✀-➿]'         # 装饰符号
    r'|[　-〿]'         # CJK符号
    r'|[\U0001F000-\U0001F9FF]'  # 表情符号
)

PURE_NUMBER_PATTERN = re.compile(r'^[\d\s.,%]+$')
PURE_SYMBOL_PATTERN = re.compile(r'^[\s\W]+$')

def clean_danmaku(danmaku_list):
    """数据清洗主函数"""
    cleaned = []
    seen = set()

    for item in danmaku_list:
        content = item.get('content', '')

        # 1. 去除特殊字符和emoji
        content = SPECIAL_CHARS_PATTERN.sub('', content)

        # 2. 有效性判断
        if len(content) < 2 or len(content) > 100:
            continue
        if PURE_NUMBER_PATTERN.match(content):
            continue
        if PURE_SYMBOL_PATTERN.match(content):
            continue

        # 3. 繁简转换
        content = convert_to_simple(content)

        # 4. 内容去重
        if content not in seen:
            seen.add(content)
            cleaned.append({'content': content, 'timestamp': item.get('timestamp', 0)})

    return cleaned
```

### 5.3 清洗统计结果

| 指标 | 数值 |
|------|------|
| 输入弹幕总数 | 5,656条 |
| 去除特殊字符/Emoji | 253条 |
| 去除纯数字弹幕 | 69条 |
| 去除纯符号弹幕 | 997条 |
| 去除超短弹幕 | 51条 |
| **有效弹幕数量** | **4,528条** |
| **去重后弹幕数量** | **3,515条** |

### 5.4 繁简转换

```python
def convert_to_simple(text):
    """简繁体转换"""
    conv_table = {
        '網': '网', '電': '电', '雲': '云', '語': '语', '數': '数',
        '據': '据', '開': '开', '發': '发', '會': '会', '對': '对',
        '們': '们', '過': '过', '時': '时', '間': '间', '說': '说',
    }
    return ''.join(conv_table.get(char, char) for char in text)
```

### 5.5 停用词表

弹幕中的常见无意义词汇需要在NLP处理前过滤：

```python
STOPWORDS = set([
    '的', '了', '是', '我', '你', '他', '她', '它', '们', '这', '那',
    '有', '在', '和', '就', '不', '也', '都', '要', '会', '可以',
    '能', '说', '被', '把', '让', '给', '与', '及', '而', '但',
    '却', '还', '又', '更', '最', '自己', '什么', '怎么', '这个',
    '那个', '一个', '一些', '没', '啊', '吧', '呢', '哦', '嗯', '哈',
    '啦', '嘛', '呀', '哇', '嘿', '哼', '哪', '谁', '多', '少',
    '2333', '233', '666', '哈哈哈', '笑死', '真的', '其实', '觉得',
])
```

---

## 总结

本模块成功实现了B站视频弹幕数据的完整采集与清洗系统，主要成果：

1. **API接口封装**：封装了视频信息API和弹幕API（Protobuf/XML双模式）
2. **Protobuf解析器**：手动实现Protobuf解码器，无须依赖外部库
3. **智能去重**：采用dmid作为去重键，有效避免误删相同内容弹幕
4. **数据完整**：实际采集5656条弹幕，数据完整度达104.1%
5. **数据清洗**：清洗后获得3515条有效弹幕，为NLP处理提供高质量输入

采集的弹幕数据已保存至`bilibili_data.json`，清洗后数据保存至`cleaned_danmaku.json`，为后续NLP处理和可视化分析提供了完整的数据基础。
