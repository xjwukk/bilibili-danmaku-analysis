# 大数据持久化存储方案

## 1. 存储方案选型对比

### 1.1 HBase（列式存储）

| 优点 | 缺点 |
|------|------|
| 高扩展性，支持PB级数据 | 配置复杂，需Hadoop生态支持 |
| 列式存储，高效压缩 | 无事务支持，不支持JOIN |
| 高并发读写，单节点支持10万+ QPS | 需要设计好rowkey避免热点 |
| 稀疏数据存储友好（弹幕场景） | 运维成本较高 |

### 1.2 HDFS（分布式文件系统）

| 优点 | 缺点 |
|------|------|
| 高吞吐量，适合批处理 | 随机读写性能差 |
| 容错性强，自动副本 | 不支持随机修改 |
| 适合存储历史数据 | 不适合实时查询 |

### 1.3 Hive（数据仓库）

| 优点 | 缺点 |
|------|------|
| SQL查询，门槛低 | 延迟高，不适合实时 |
| 与Hadoop无缝集成 | 批量处理场景更合适 |
| 生态成熟 |  |

### 1.4 MySQL/PostgreSQL（关系型数据库）

| 优点 | 缺点 |
|------|------|
| 事务支持(ACID) | 单机容量有限 |
| SQL成熟生态 | 分布式扩展复杂 |
| 适合结构化数据 | 弹幕量级下成本高 |

### 1.5 MongoDB（文档型数据库）

| 优点 | 缺点 |
|------|------|
| 文档存储，JSON友好 | 全文检索不如ES |
| 水平扩展能力强 | 一致性保证较弱 |
| 灵活schema |  |

## 2. 选择理由：为什么选择HBase

1. **弹幕数据特性匹配**：
   - 数据量大（视频弹幕可达数万条）
   - 写入频率高（视频发布时集中爆发）
   - 读取模式以时间顺序为主

2. **技术优势**：
   - RowKey设计灵活，支持按视频ID+时间范围高效查询
   - 列式存储，弹幕属性（颜色、发送时间等）独立存储，节省空间
   - 与Hadoop生态兼容，可复用MapReduce进行离线分析

3. **实际案例参考**：
   - bilibili弹幕存储采用类似架构
   - 各大视频网站的弹幕系统均采用列式存储方案

## 3. 数据模型设计

### 3.1 视频信息表：video_info

```
RowKey: BV_ID (e.g., BV1jEAaz3E6K)
```

| 列族 | 列 | 说明 |
|------|-----|------|
| info | title | 视频标题 |
| info | author | 作者名称 |
| info | author_mid | 作者MID |
| info | publish_date | 发布日期时间戳 |
| info | duration | 视频时长(秒) |
| info | description | 视频描述 |
| stats | view_count | 播放量 |
| stats | like_count | 点赞数 |
| stats | coin_count | 投币数 |
| stats | favorite_count | 收藏数 |
| stats | danmaku_count | 弹幕数 |
| stats | reply_count | 评论数 |
| stats | share_count | 分享数 |
| stats | last_updated | 最后更新时间 |

### 3.2 弹幕数据表：danmaku_data

```
RowKey: BV_ID + timestamp(8位) + dmid(雪花ID)

例如: BV1jEAaz3E6K_00000001_2060848104261108480
```

| 列族 | 列 | 说明 |
|------|-----|------|
| content | text | 弹幕文本内容 |
| content | send_time | 发送时间戳 |
| meta | user_id | 发送者UID |
| meta | is_upper | 是否是UP主(0/1) |
| meta | color | 弹幕颜色(十进制) |
| meta | color_hex | 弹幕颜色(十六进制) |
| meta | mode | 弹幕类型(1横2竖3高级4底部) |
| meta | font_size | 字号 |
| meta | pool | 弹幕池(0普通1字幕2特殊) |

### 3.3 词频统计表：wordfreq_data

```
RowKey: BV_ID + word

例如: BV1jEAaz3E6K_AI
```

| 列族 | 列 | 说明 |
|------|-----|------|
| stats | freq | 词频 |
| stats | sentiment_pos | 正面情感计数 |
| stats | sentiment_neg | 负面情感计数 |
| stats | sentiment_neu | 中性情感计数 |

## 4. HBase Shell常用命令

```bash
# 连接HBase Shell
hbase shell

# 创建命名空间
create_namespace 'bilibili'

# 创建视频信息表
create 'video_info', 'info', 'stats'

# 创建弹幕数据表
create 'danmaku_data', 'content', 'meta'

# 创建词频统计表
create 'wordfreq_data', 'stats'

# 查看表列表
list

# 查看表结构
describe 'danmaku_data'

# 启用表
enable 'danmaku_data'

# 禁用表
disable 'danmaku_data'

# 统计行数
count 'danmaku_data'

# 获取单行数据
get 'danmaku_data', 'BV1jEAaz3E6K'

# 扫描数据（限制10行）
scan 'danmaku_data', {LIMIT => 10}

# 范围扫描
scan 'danmaku_data', {STARTROW => 'BV1jEAaz3E6K', STOPROW => 'BV1jEAaz3E6K_99999999'}

# 删除数据
delete 'danmaku_data', 'BV1jEAaz3E6K_00000001_dmid', 'content:text'

# 删除表
disable 'danmaku_data'
drop 'danmaku_data'
```

## 5. 环境配置

### 5.1 伪分布式配置（单机）

1. **配置Hadoop core-site.xml**
```xml
<configuration>
    <property>
        <name>fs.defaultFS</name>
        <value>hdfs://localhost:9000</value>
    </property>
    <property>
        <name>hadoop.tmp.dir</name>
        <value>/tmp/hadoop</value>
    </property>
</configuration>
```

2. **配置HBase hbase-site.xml**
```xml
<configuration>
    <property>
        <name>hbase.cluster.distributed</name>
        <value>true</value>
    </property>
    <property>
        <name>hbase.rootdir</name>
        <value>hdfs://localhost:9000/hbase</value>
    </property>
    <property>
        <name>hbase.zookeeper.property.dataDir</name>
        <value>/tmp/zookeeper</value>
    </property>
</configuration>
```

### 5.2 Zookeeper配置

```properties
# zoo.cfg
dataDir=/tmp/zookeeper
clientPort=2181
server.1=localhost:2888:3888
```

## 6. 参考项目

- [bilibili-danmaku-analysis](https://github.com/rain8883/bilibili-danmaku-analysis)
- [danmaku-spider](https://github.com/rain8883/danmaku-spider)
- [hbase-examples](https://github.com/rain8883/hbase-examples)