# -*- coding: utf-8 -*-
"""
关键词共现网络分析
分析词语之间的共现关系，构建词语网络
"""

import json
import os
import re
from collections import defaultdict
import math

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
WORDFREQ_PATH = os.path.join(NLP_DIR, 'wordfreq.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'word_cooccurrence.json')

# 停用词表
STOPWORDS = {
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '知道', '这',
    '那', '什么', '怎么', '为什么', '这个', '那个', '我们', '他们', '你们', '大家',
    '可以', '因为', '所以', '但是', '如果', '虽然', '然后', '其实', '觉得', '应该',
    '可能', '已经', '自己', '现在', '这样', '那样', '这里', '那里', '开始', '一直',
    '还是', '只有', '只能', '还有', '还有', '还有', '不是', '还是', '就是', '这些',
    '那些', '哪些', '一样', '一下', '一点', '真的', '终于', '终于', '2333', '233',
    '哈哈哈', '哈哈', '笑死', 'nb', '牛逼', '666', '确实', '其实', '反正', '确实'
}


def load_data():
    """加载弹幕和词频数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        cleaned = json.load(f)

    wordfreq = {}
    if os.path.exists(WORDFREQ_PATH):
        with open(WORDFREQ_PATH, 'r', encoding='utf-8') as f:
            wf = json.load(f)
            for item in wf.get('top_100', []):
                wordfreq[item['word']] = item['freq']

    return cleaned['danmaku_list'], wordfreq


def segment_text(text):
    """
    简单分词（基于字符级别+常见词组）
    实际使用jieba效果更好
    """
    import jieba
    words = jieba.cut(text)
    return [w for w in words if w.strip() and len(w) > 1 and w not in STOPWORDS]


def build_cooccurrence_network(danmaku_list, wordfreq, top_n=50, window_size=3):
    """
    构建词语共现网络

    参数:
        danmaku_list: 弹幕列表
        wordfreq: 词频统计
        top_n: 只考虑top N高频词
        window_size: 共现窗口大小（同一弹幕内相邻词语视为共现）

    返回:
        cooccurrence_network: 共现网络分析结果
    """
    print('\n[关键词共现网络分析]')

    # 取top N高频词作为网络节点
    sorted_words = sorted(wordfreq.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_words = {word for word, freq in sorted_words}
    word_set = set(top_words)

    print(f'    网络节点数（高频词）: {len(top_words)}')

    # 统计共现次数
    cooccurrence_counts = defaultdict(lambda: defaultdict(int))

    for d in danmaku_list:
        content = d.get('content', '')

        # 分词
        words = segment_text(content)

        # 在窗口内统计共现
        for i, word1 in enumerate(words):
            if word1 not in word_set:
                continue

            # 窗口内的其他词
            for j in range(max(0, i - window_size), min(len(words), i + window_size + 1)):
                if i == j:
                    continue
                word2 = words[j]
                if word2 in word_set:
                    cooccurrence_counts[word1][word2] += 1

    # 计算节点统计数据
    node_stats = defaultdict(lambda: {'freq': 0, 'cooccurrence_count': 0, 'cooccur_words': {}})

    for word in top_words:
        node_stats[word]['freq'] = wordfreq.get(word, 0)

    # 构建边列表
    edges = []
    edge_set = set()

    for word1, related_words in cooccurrence_counts.items():
        for word2, count in related_words.items():
            if word1 < word2:  # 避免重复边
                edge_key = (word1, word2)
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({
                        'source': word1,
                        'target': word2,
                        'weight': count
                    })

    # 按权重排序
    edges.sort(key=lambda x: x['weight'], reverse=True)

    # 取top边
    top_edges = edges[:100]

    # 计算节点度数
    node_degrees = defaultdict(int)
    for edge in edges:
        node_degrees[edge['source']] += 1
        node_degrees[edge['target']] += 1

    # 构建节点列表
    nodes = []
    for word in top_words:
        nodes.append({
            'name': word,
            'freq': wordfreq.get(word, 0),
            'degree': node_degrees[word],
            'category': _get_word_category(word)  # 简单分类
        })

    # 按度数排序节点
    nodes.sort(key=lambda x: x['degree'], reverse=True)

    # 计算网络统计
    total_edges = len(edges)
    avg_degree = sum(node_degrees.values()) / len(nodes) if nodes else 0
    max_degree = max(node_degrees.values()) if node_degrees else 0

    # 高共现词对
    high_cooccurrence_pairs = [
        {
            'word1': e['source'],
            'word2': e['target'],
            'count': e['weight']
        }
        for e in top_edges[:20]
    ]

    # 词语类别
    category_words = defaultdict(list)
    for node in nodes[:30]:
        cat = node['category']
        category_words[cat].append(node['name'])

    result = {
        'network_stats': {
            'node_count': len(nodes),
            'edge_count': total_edges,
            'avg_degree': round(avg_degree, 2),
            'max_degree': max_degree,
            'density': round(total_edges / (len(nodes) * (len(nodes) - 1) / 2), 4) if len(nodes) > 1 else 0
        },
        'nodes': nodes[:50],  # 最多50个节点
        'edges': top_edges,
        'top_cooccurrence_pairs': high_cooccurrence_pairs,
        'category_words': dict(category_words)
    }

    # 打印结果
    print(f'    网络节点数: {len(nodes)}')
    print(f'    网络边数: {total_edges}')
    print(f'    平均度数: {avg_degree:.2f}')
    print(f'    最大度数: {max_degree}')
    print(f'    网络密度: {result["network_stats"]["density"]}')
    print(f'    高共现词对Top5:')
    for pair in high_cooccurrence_pairs[:5]:
        print(f'        {pair["word1"]} - {pair["word2"]}: {pair["count"]}次')

    return result


def _get_word_category(word):
    """
    简单词语分类
    实际应用中可用更复杂的语义分类
    """
    # 情感词
    positive_words = {'好', '棒', '强', '牛', '赞', '喜欢', '爱', '酷', '帅', '优秀', '精彩', '完美', 'nb', '厉害'}
    negative_words = {'烂', '差', '垃圾', '蠢', '傻', '无聊', '尴尬', '无语', '失望', '恶心', '弱'}

    if word in positive_words:
        return 'positive'
    elif word in negative_words:
        return 'negative'
    elif len(word) == 2:
        return 'short'
    elif word.isdigit():
        return 'number'
    else:
        return 'neutral'


def main():
    print('=' * 70)
    print('关键词共现网络分析')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载数据...')
    danmaku_list, wordfreq = load_data()
    print(f'    弹幕数量: {len(danmaku_list)}')
    print(f'    词频数据: {len(wordfreq)}个词')

    # 构建共现网络
    result = build_cooccurrence_network(danmaku_list, wordfreq, top_n=50)

    # 保存结果
    print(f'\n[2] 保存结果...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('共现网络分析完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    main()
