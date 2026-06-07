# -*- coding: utf-8 -*-
"""
情感趋势分析
分析视频播放过程中情感变化趋势，按时间段聚合情感得分
"""

import json
import os
from collections import defaultdict

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'nlp_processing')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
SENTIMENT_PATH = os.path.join(NLP_DIR, 'sentiment.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'sentiment_trend.json')


def load_data():
    """加载弹幕和情感数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        cleaned = json.load(f)

    sentiment_map = {}
    if os.path.exists(SENTIMENT_PATH):
        with open(SENTIMENT_PATH, 'r', encoding='utf-8') as f:
            sentiment = json.load(f)
            for item in sentiment.get('details', []):
                sentiment_map[item['content']] = {
                    'sentiment': item['sentiment'],
                    'pos_score': item.get('pos_score', 0),
                    'neg_score': item.get('neg_score', 0),
                    'confidence': item.get('confidence', 0)
                }

    return cleaned['danmaku_list'], sentiment_map


def sentiment_to_score(sentiment):
    """将情感标签转换为数值分数"""
    if sentiment == 'positive':
        return 1.0
    elif sentiment == 'negative':
        return -1.0
    else:
        return 0.0


def analyze_sentiment_trend(danmaku_list, sentiment_map, bucket_size=60):
    """
    分析情感趋势

    参数:
        danmaku_list: 弹幕列表
        sentiment_map: 情感分析结果映射
        bucket_size: 时间桶大小（秒），默认60秒

    返回:
        sentiment_trend: 情感趋势分析结果
    """
    print('\n[情感趋势分析]')

    # 按时间桶聚合
    time_buckets = defaultdict(lambda: {
        'positive': 0,
        'negative': 0,
        'neutral': 0,
        'total_score': 0,
        'count': 0,
        'danmaku_contents': []
    })

    for d in danmaku_list:
        timestamp = d.get('timestamp', 0)
        if timestamp <= 0:
            continue

        content = d.get('content', '')
        bucket_idx = int(timestamp / bucket_size)

        # 获取情感信息
        senti_info = sentiment_map.get(content, {'sentiment': 'neutral', 'pos_score': 0, 'neg_score': 0})
        sentiment = senti_info['sentiment']

        # 更新统计
        bucket = time_buckets[bucket_idx]
        bucket['count'] += 1
        bucket['sentiment'] = sentiment
        bucket['total_score'] += sentiment_to_score(sentiment)

        if sentiment == 'positive':
            bucket['positive'] += 1
        elif sentiment == 'negative':
            bucket['negative'] += 1
        else:
            bucket['neutral'] += 1

        # 收集部分弹幕内容作为样本
        if len(bucket['danmaku_contents']) < 5:
            bucket['danmaku_contents'].append(content)

    # 转换为列表并排序
    sorted_buckets = sorted(time_buckets.items(), key=lambda x: x[0])

    # 构建趋势数据
    trend_data = []
    for bucket_idx, stats in sorted_buckets:
        time_seconds = bucket_idx * bucket_size
        avg_score = stats['total_score'] / stats['count'] if stats['count'] > 0 else 0

        # 计算情感比例
        total = stats['positive'] + stats['negative'] + stats['neutral']
        pos_ratio = stats['positive'] / total if total > 0 else 0
        neg_ratio = stats['negative'] / total if total > 0 else 0
        neu_ratio = stats['neutral'] / total if total > 0 else 0

        trend_data.append({
            'time_bucket': time_seconds,
            'time_label': f"{time_seconds // 60:.0f}:{time_seconds % 60:02.0f}",
            'danmaku_count': stats['count'],
            'avg_sentiment_score': round(avg_score, 3),
            'positive_ratio': round(pos_ratio, 3),
            'negative_ratio': round(neg_ratio, 3),
            'neutral_ratio': round(neu_ratio, 3),
            'dominant_sentiment': 'positive' if stats['positive'] > stats['negative'] and stats['positive'] > stats['neutral'] else ('negative' if stats['negative'] > stats['neutral'] else 'neutral'),
            'sample_danmaku': stats['danmaku_contents'][:3]
        })

    # 识别情感高峰和低谷
    if trend_data:
        sorted_by_score = sorted(trend_data, key=lambda x: x['avg_sentiment_score'], reverse=True)
        peak = sorted_by_score[0]  # 最高情感时刻
        valley = sorted_by_score[-1]  # 最低情感时刻
    else:
        peak = valley = None

    # 按时段分组统计
    segment_stats = {
        '0-5min': {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0},
        '5-10min': {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0},
        '10-15min': {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0},
        '15-20min': {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0},
        '20min+': {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
    }

    for item in trend_data:
        seconds = item['time_bucket']
        minutes = seconds / 60

        if minutes < 5:
            seg = segment_stats['0-5min']
        elif minutes < 10:
            seg = segment_stats['5-10min']
        elif minutes < 15:
            seg = segment_stats['10-15min']
        elif minutes < 20:
            seg = segment_stats['15-20min']
        else:
            seg = segment_stats['20min+']

        seg['total'] += item['danmaku_count']
        if item['dominant_sentiment'] == 'positive':
            seg['positive'] += item['danmaku_count']
        elif item['dominant_sentiment'] == 'negative':
            seg['negative'] += item['danmaku_count']
        else:
            seg['neutral'] += item['danmaku_count']

    # 计算整体情感统计
    total_pos = sum(s['positive'] for s in segment_stats.values())
    total_neg = sum(s['negative'] for s in segment_stats.values())
    total_neu = sum(s['neutral'] for s in segment_stats.values())
    total_all = total_pos + total_neg + total_neu

    result = {
        'bucket_size_seconds': bucket_size,
        'trend_data': trend_data,
        'peak_moment': peak,
        'valley_moment': valley,
        'segment_stats': segment_stats,
        'overall_stats': {
            'positive_count': total_pos,
            'negative_count': total_neg,
            'neutral_count': total_neu,
            'positive_ratio': round(total_pos / total_all, 3) if total_all > 0 else 0,
            'negative_ratio': round(total_neg / total_all, 3) if total_all > 0 else 0,
            'neutral_ratio': round(total_neu / total_all, 3) if total_all > 0 else 0
        }
    }

    # 打印结果
    print(f'    分析时段数: {len(trend_data)}')
    print(f'    正面最多时段: {peak["time_label"] if peak else "N/A"} (评分: {peak["avg_sentiment_score"] if peak else 0:.3f})')
    print(f'    负面最多时段: {valley["time_label"] if valley else "N/A"} (评分: {valley["avg_sentiment_score"] if valley else 0:.3f})')
    print(f'    时段统计: {segment_stats}')

    return result


def main():
    print('=' * 70)
    print('情感趋势分析')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载数据...')
    danmaku_list, sentiment_map = load_data()
    print(f'    弹幕数量: {len(danmaku_list)}')
    print(f'    情感数据: {len(sentiment_map)}条')

    # 分析情感趋势
    result = analyze_sentiment_trend(danmaku_list, sentiment_map)

    # 保存结果
    print(f'\n[2] 保存结果...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('情感趋势分析完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    main()
