# -*- coding: utf-8 -*-
"""
用户行为分析
基于用户ID分析发送弹幕次数、活跃时段、情感倾向等
"""

import json
import os
from collections import defaultdict
from datetime import datetime

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
SENTIMENT_PATH = os.path.join(NLP_DIR, 'sentiment.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'user_behavior.json')


def load_data():
    """加载弹幕和情感数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        cleaned = json.load(f)

    sentiment_data = {}
    if os.path.exists(SENTIMENT_PATH):
        with open(SENTIMENT_PATH, 'r', encoding='utf-8') as f:
            sentiment = json.load(f)
            # 构建情感映射
            for item in sentiment.get('details', []):
                sentiment_data[item['content']] = item['sentiment']

    return cleaned['danmaku_list'], sentiment_data


def analyze_user_behavior(danmaku_list, sentiment_data):
    """
    分析用户行为

    参数:
        danmaku_list: 弹幕列表
        sentiment_data: 情感分析结果映射

    返回:
        user_behavior: 用户行为分析结果
    """
    print('\n[用户行为分析]')

    # 用户统计数据
    user_stats = defaultdict(lambda: {
        'danmaku_count': 0,
        'timestamps': [],
        'contents': [],
        'sentiments': [],
        'pool_type': defaultdict(int),  # 弹幕池类型
        'mode_type': defaultdict(int),  # 弹幕模式
    })

    # 遍历所有弹幕
    for d in danmaku_list:
        user_id = d.get('user_id', '')
        if not user_id or user_id == 'anonymous':
            user_id = f"anon_{hash(d.get('content', '')) % 1000000}"  # 匿名用户

        timestamp = d.get('timestamp', 0)
        content = d.get('content', '')
        pool = d.get('pool', 0)
        mode = d.get('mode', 0)

        user_stats[user_id]['danmaku_count'] += 1
        user_stats[user_id]['timestamps'].append(timestamp)
        user_stats[user_id]['contents'].append(content)
        user_stats[user_id]['pool_type'][pool] += 1
        user_stats[user_id]['mode_type'][mode] += 1

        # 情感倾向
        sentiment = sentiment_data.get(content, 'neutral')
        user_stats[user_id]['sentiments'].append(sentiment)

    # 计算用户排名
    user_rankings = sorted(
        user_stats.items(),
        key=lambda x: x[1]['danmaku_count'],
        reverse=True
    )

    # Top 20 活跃用户
    top20_active_users = []
    for user_id, stats in user_rankings[:20]:
        sentiments = stats['sentiments']
        pos_count = sentiments.count('positive')
        neg_count = sentiments.count('negative')
        neu_count = sentiments.count('neutral')

        top20_active_users.append({
            'user_id': str(user_id)[:20],  # 截断显示
            'danmaku_count': stats['danmaku_count'],
            'positive_count': pos_count,
            'negative_count': neg_count,
            'neutral_count': neu_count,
            'dominant_sentiment': 'positive' if pos_count > neg_count else ('negative' if neg_count > pos_count else 'neutral'),
            'pool_distribution': dict(stats['pool_type']),
            'mode_distribution': dict(stats['mode_type']),
            'sample_contents': stats['contents'][:3]  # 最近3条弹幕示例
        })

    # 活跃度分布
    danmaku_count_dist = defaultdict(int)
    for user_id, stats in user_stats.items():
        count = stats['danmaku_count']
        if count == 1:
            danmaku_count_dist['1条'] += 1
        elif count == 2:
            danmaku_count_dist['2条'] += 1
        elif count == 3:
            danmaku_count_dist['3条'] += 1
        elif count <= 5:
            danmaku_count_dist['4-5条'] += 1
        elif count <= 10:
            danmaku_count_dist['6-10条'] += 1
        else:
            danmaku_count_dist['10条以上'] += 1

    # 用户情感统计
    user_sentiment_stats = {
        'positive_users': 0,
        'negative_users': 0,
        'neutral_users': 0,
        'mixed_users': 0
    }

    for user_id, stats in user_stats.items():
        sentiments = stats['sentiments']
        pos_count = sentiments.count('positive')
        neg_count = sentiments.count('negative')
        neu_count = sentiments.count('neutral')

        if pos_count > neg_count and pos_count > neu_count:
            user_sentiment_stats['positive_users'] += 1
        elif neg_count > pos_count and neg_count > neu_count:
            user_sentiment_stats['negative_users'] += 1
        elif neu_count >= pos_count and neu_count >= neg_count:
            user_sentiment_stats['neutral_users'] += 1
        else:
            user_sentiment_stats['mixed_users'] += 1

    # 高互动用户（发送>=3条弹幕）
    highly_active_users = [
        {
            'user_id': str(user_id)[:20],
            'count': stats['danmaku_count'],
            'sentiment': 'positive' if stats['sentiments'].count('positive') > stats['sentiments'].count('negative') else 'negative'
        }
        for user_id, stats in user_rankings
        if stats['danmaku_count'] >= 3
    ]

    result = {
        'total_unique_users': len(user_stats),
        'total_danmaku': len(danmaku_list),
        'avg_danmaku_per_user': round(len(danmaku_list) / len(user_stats), 2) if user_stats else 0,
        'top20_active_users': top20_active_users,
        'danmaku_count_distribution': dict(danmaku_count_dist),
        'user_sentiment_distribution': user_sentiment_stats,
        'highly_active_user_count': len(highly_active_users),
        'highly_active_users_sample': highly_active_users[:10]
    }

    # 打印结果
    print(f'    独立用户数: {len(user_stats)}')
    print(f'    总弹幕数: {len(danmaku_list)}')
    print(f'    人均弹幕: {result["avg_danmaku_per_user"]}条')
    print(f'    活跃用户分布: {dict(danmaku_count_dist)}')
    print(f'    用户情感分布: {user_sentiment_stats}')
    print(f'    高互动用户(>=3条): {len(highly_active_users)}')

    return result


def main():
    print('=' * 70)
    print('用户行为分析')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载数据...')
    danmaku_list, sentiment_data = load_data()
    print(f'    弹幕数量: {len(danmaku_list)}')
    print(f'    情感数据: {len(sentiment_data)}条')

    # 分析用户行为
    result = analyze_user_behavior(danmaku_list, sentiment_data)

    # 保存结果
    print(f'\n[2] 保存结果...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('用户行为分析完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    main()
