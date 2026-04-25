# HBase 表结构设计文档

## 1. 设计原则

### 1.1 RowKey设计
- **唯一性**: 每行数据必须由唯一的RowKey标识
- **有序性**: HBase按RowKey字典序排序，合理设计可优化范围扫描
- **避免热点**: RowKey前缀应分散，防止数据写入集中在少数节点

### 1.2 列族设计
- 列族不宜过多（建议1-3个），每个列族下可包含任意数量的列
- 将访问频率高的列放在同一列族
- 稀疏存储：弹幕属性（颜色、发送时间等）独立存储，节省空间

## 2. 表结构

### 2.1 video_info - 视频信息表

```
表名: video_info
命名空间: bilibili
```

| RowKey | 列族 | 列 | 数据类型 | 说明 |
|--------|------|-----|----------|------|
| BV_ID | info | title | String | 视频标题 |
| BV_ID | info | author | String | UP主名称 |
| BV_ID | info | author_mid | Long | UP主MID |
| BV_ID | info | publish_date | Long | 发布时间戳 |
| BV_ID | info | duration | Int | 视频时长(秒) |
| BV_ID | info | description | String | 视频描述 |
| BV_ID | info | cid | Long | 视频CID |
| BV_ID | stats | view_count | Long | 播放量 |
| BV_ID | stats | like_count | Long | 点赞数 |
| BV_ID | stats | coin_count | Long | 投币数 |
| BV_ID | stats | favorite_count | Long | 收藏数 |
| BV_ID | stats | danmaku_count | Long | 弹幕数 |
| BV_ID | stats | reply_count | Long | 评论数 |
| BV_ID | stats | share_count | Long | 分享数 |
| BV_ID | stats | last_updated | Long | 最后更新时间 |

**RowKey示例**: `BV1jEAaz3E6K`

**特点**:
- 写入频率低，每视频一行
- 读取时按BV_ID精确查询
- 可定期更新统计数据

### 2.2 danmaku_data - 弹幕数据表

```
表名: danmaku_data
命名空间: bilibili
```

| RowKey | 列族 | 列 | 数据类型 | 说明 |
|--------|------|-----|----------|------|
| BV+TS+DMID | content | text | String | 弹幕文本内容 |
| BV+TS+DMID | content | send_time | Long | 发送时间戳 |
| BV+TS+DMID | content | timestamp | Float | 视频内时间(秒) |
| BV+TS+DMID | meta | user_id | String | 发送者UID |
| BV+TS+DMID | meta | is_upper | Int | 是否UP主(0/1) |
| BV+TS+DMID | meta | color | Int | 颜色(十进制) |
| BV+TS+DMID | meta | color_hex | String | 颜色(十六进制) |
| BV+TS+DMID | meta | mode | Int | 类型(1横2竖3高级4底部) |
| BV+TS+DMID | meta | font_size | Int | 字号 |
| BV+TS+DMID | meta | pool | Int | 弹幕池(0普通1字幕2特殊) |

**RowKey格式**: `{BV_ID}_{timestamp(8位)}_{dmid}`

**示例**: `BV1jEAaz3E6K_00000644_2060848104261108480`

**设计理由**:
1. `BV_ID` 前缀确保同一视频弹幕在一起
2. `timestamp` 用于按时间范围查询
3. `dmid` 确保RowKey唯一性

**特点**:
- 高写入频率，视频发布时集中写入
- 读取模式：按BV查询全部，或按时间范围查询
- 时间戳升序排列，扫描时按视频时间顺序

### 2.3 wordfreq_data - 词频统计表

```
表名: wordfreq_data
命名空间: bilibili
```

| RowKey | 列族 | 列 | 数据类型 | 说明 |
|--------|------|-----|----------|------|
| BV+WORD | stats | freq | Int | 词频 |
| BV+WORD | stats | sentiment_pos | Int | 正面情感计数 |
| BV+WORD | stats | sentiment_neg | Int | 负面情感计数 |
| BV+WORD | stats | sentiment_neu | Int | 中性情感计数 |

**RowKey格式**: `{BV_ID}_{word}`

**示例**: `BV1jEAaz3E6K_AI`

**特点**:
- MapReduce统计结果的持久化存储
- 可按视频+词进行前缀扫描
- 支持TopK查询

## 3. HBase Shell 建表语句

```bash
# 连接HBase Shell
hbase shell

# 创建命名空间
create_namespace 'bilibili'

# 创建视频信息表
create 'bilibili:video_info', 'info', 'stats'

# 创建弹幕数据表
create 'bilibili:danmaku_data', 'content', 'meta'

# 创建词频统计表
create 'bilibili:wordfreq_data', 'stats'
```

## 4. Region分裂策略

### danmaku_data 表
- 预分区：创建时指定12-24个region
- 分裂时机：单个region达到10GB时自动分裂
- RowKey设计确保数据均匀分布

### video_info 表
- 数据量小，通常单region即可
- 可关闭自动分裂

## 5. 性能优化建议

1. **Bloom Filter**: 为danmaku_data表启用Bloom Filter加速不存在行查询
2. **Block Cache**: 视频信息表适合放入Block Cache加速读取
3. **压缩**: 弹幕表可启用GZIP压缩减少存储空间
4. **TTL**: 弹幕数据建议设置90-180天TTL自动清理

```bash
# 创建表时指定压缩和Bloom Filter
create 'bilibili:danmaku_data', {NAME => 'content', COMPRESSION => 'GZ', BLOOMFILTER => 'ROW'}
```