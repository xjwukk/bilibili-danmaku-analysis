# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a course project for "大数据应用系统开发实践" (Big Data Application System Development Practice). The project implements a Bilibili video danmaku (bullet comments) data analysis system with 5 main modules.

**Target Video:** BV1jEAaz3E6K (一个视频搞懂OpenClaw！) - 518万播放, 5400+弹幕

## Architecture

```
agent1_crawler/     - Bilibili video & danmaku crawler
agent2_nlp/         - NLP processing (cleaning, word frequency, sentiment, LDA, wordcloud)
agent3_storage/     - HBase persistent storage design
agent4_frontend/    - Web visualization (ECharts wordcloud & charts)
agent5_report/     - Course design reports (3 students)
```

## Running the Crawler

The main crawler is `agent1_crawler/bilibili_crawler.py`. It requires:
1. Valid Bilibili SESSDATA cookie in the COOKIE variable (line ~13)
2. Python 3.7+ with `requests` library

```bash
cd agent1_crawler
python bilibili_crawler.py
```

Output: `bilibili_data.json` with video_info and danmaku_list (~3600-4500 danmaku with valid cookie, ~1200 without)

## NLP Pipeline

The NLP module (`agent2_nlp/`) has a multi-stage pipeline:

| Stage | File | Purpose |
|-------|------|---------|
| Cleaning | `clean_danmaku.py` | Remove spam, filter by length, deduplicate |
| Sentiment | `sentiment_lexicon.py` | SnowNLP-based sentiment scoring with lexicon |
| Word Frequency | `nlp_process.py` | jieba segmentation, stopword filtering, word count |
| LDA Topics | `lda_sentiment_topics.py` | Gensim LDA topic modeling on positive/negative segments |
| Wordcloud | `generate_wordcloud.py` | ECharts-compatible wordcloud generation |

Running the full NLP pipeline:
```bash
cd agent2_nlp
python clean_danmaku.py   # → cleaned_danmaku.json
python nlp_process.py    # → wordfreq.json
python sentiment_lexicon.py   # → sentiment.json, positive_danmakus.json, negative_danmakus.json
python lda_sentiment_topics.py  # → lda_sentiment_topics.json, sentiment_distribution.json
python sentiment_distribution.py  # → sentiment_distribution.png
```

## Data Flow

1. **Crawler** → `bilibili_data.json` (video info + raw danmaku)
2. **Clean** → `cleaned_danmaku.json`
3. **NLP** → `wordfreq.json`, `sentiment.json`, `lda_sentiment_topics.json`, `positive_danmakus.json`, `negative_danmakus.json`
4. **Storage** → HBase tables (video_info, danmaku_data, wordfreq_data)
5. **Frontend** → HTML pages reading from NLP output JSON files

## Key Files

| File | Purpose |
|------|---------|
| `agent1_crawler/bilibili_crawler.py` | Main crawler with protobuf parsing |
| `agent1_crawler/bilibili_data.json` | Crawled data (video + danmaku, ~1.4MB) |
| `agent2_nlp/nlp_process.py` | Chinese segmentation, stopword filtering |
| `agent2_nlp/sentiment_lexicon.py` | SnowNLP sentiment scoring |
| `agent2_nlp/lda_sentiment_topics.py` | Gensim LDA topic modeling |
| `agent2_nlp/wordfreq.json` | Word frequency statistics |
| `agent2_nlp/cleaned_danmaku.json` | Cleaned danmaku data |
| `agent3_storage/hbase_writer.py` | HBase data writer |
| `agent4_frontend/index.html` | Wordcloud visualization page |
| `agent4_frontend/charts.html` | Sentiment distribution charts |

## Bilibili API Notes

- Video info: `https://api.bilibili.com/x/web-interface/view?bvid={BV_ID}`
- Danmaku (protobuf, primary): `https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={CID}&pid={AID}&segment_index={N}`
- Danmaku (XML, fallback): `https://comment.bilibili.com/{CID}.xml`
- Full danmaku (segmented) requires valid SESSDATA cookie due to WBI signature protection

## Report Templates

Three student reports in `agent5_report/`:
- 报告A_爬虫.md (Student A - Crawler)
- 报告B_NLP.md (Student B - NLP)
- 报告C_存储前端.md (Student C - Storage & Frontend)
