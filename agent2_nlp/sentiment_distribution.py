# -*- coding: utf-8 -*-
"""
弹幕情感分布概率密度数据
使用SnowNLP分析弹幕情感得分，输出JSON数据供ECharts使用
"""

import json
import os
import numpy as np
from snownlp import SnowNLP

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'sentiment_distribution.json')


def load_danmaku():
    """加载弹幕数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['danmaku_list']


def analyze_sentiment_scores(danmaku_list):
    """
    使用SnowNLP分析每条弹幕的情感得分

    返回:
        scores: 情感得分列表 (0-1, 越高越积极)
    """
    print('[SnowNLP情感分析]')
    scores = []

    for i, item in enumerate(danmaku_list):
        content = item['content']
        try:
            s = SnowNLP(content)
            score = s.sentiments  # 0-1之间的概率
            scores.append(score)
        except:
            scores.append(0.5)  # 默认中性

        if (i + 1) % 500 == 0:
            print(f'    已分析: {i + 1}/{len(danmaku_list)}')

    print(f'    分析完成, 共{len(scores)}条弹幕')
    return scores


def calculate_distribution_data(scores):
    """
    计算分布数据（直方图 + 统计信息）

    返回:
        histogram: 直方图数据
        stats: 统计信息
    """
    scores_array = np.array(scores)

    # 直方图数据（20个区间）
    hist, bin_edges = np.histogram(scores_array, bins=20, density=True)
    histogram = []
    for i in range(len(hist)):
        histogram.append({
            'range': f'{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}',
            'value': float(hist[i]),
            'count': int(np.sum((scores_array >= bin_edges[i]) & (scores_array < bin_edges[i+1])))
        })

    # 统计信息
    stats = {
        'mean': float(np.mean(scores_array)),
        'median': float(np.median(scores_array)),
        'std': float(np.std(scores_array)),
        'min': float(np.min(scores_array)),
        'max': float(np.max(scores_array)),
        'total': len(scores)
    }

    return histogram, stats


def main():
    print('=' * 60)
    print('弹幕情感分布分析')
    print('=' * 60)

    # 1. 加载弹幕
    print('\n[1] 加载弹幕数据...')
    danmaku_list = load_danmaku()
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 2. 情感分析
    print('\n[2] SnowNLP情感分析...')
    scores = analyze_sentiment_scores(danmaku_list)

    # 3. 计算分布数据
    print('\n[3] 计算分布数据...')
    histogram, stats = calculate_distribution_data(scores)

    print(f'    情感得分均值: {stats["mean"]:.3f}')
    print(f'    情感得分中位数: {stats["median"]:.3f}')
    print(f'    情感得分标准差: {stats["std"]:.3f}')

    # 4. 保存JSON数据
    result = {
        'histogram': histogram,
        'stats': stats
    }

    print('\n[4] 保存JSON数据...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    数据已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 60)
    print('分析完成!')
    print('=' * 60)


if __name__ == '__main__':
    main()