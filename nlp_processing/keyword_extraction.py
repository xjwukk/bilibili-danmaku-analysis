# -*- coding: utf-8 -*-
"""
关键词抽取
使用TF-IDF和TextRank算法抽取关键词
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
NLP_DIR = os.path.join(BASE_DIR, 'nlp_processing')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')
OUTPUT_PATH = os.path.join(NLP_DIR, 'keywords.json')

# 停用词表
STOPWORDS = {
    '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
    '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '知道', '这',
    '那', '什么', '怎么', '为什么', '这个', '那个', '我们', '他们', '你们', '大家',
    '可以', '因为', '所以', '但是', '如果', '虽然', '然后', '其实', '觉得', '应该',
    '可能', '已经', '自己', '现在', '这样', '那样', '这里', '那里', '开始', '一直',
    '还是', '只有', '只能', '还有', '不是', '还是', '就是', '这些', '那些', '哪些',
    '一样', '一下', '一点', '真的', '终于', '2333', '233', '哈哈哈', '哈哈', '笑死',
    'nb', '牛逼', '666', '确实', '反正', '确实', '真的', '感觉', '应该', '看来'
}


def load_cleaned_data():
    """加载清洗后的弹幕数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['danmaku_list']


def segment_text(text):
    """分词"""
    import jieba
    words = jieba.cut(text)
    return [w for w in words if w.strip() and len(w) > 1 and w not in STOPWORDS]


def tfidf_keyword_extraction(documents, top_n=30):
    """
    TF-IDF关键词抽取

    参数:
        documents: 文档列表（每条弹幕为一个文档）
        top_n: 返回top N关键词

    返回:
        tfidf_scores: TF-IDF得分
    """
    print('    [TF-IDF计算]')

    # 统计词频
    doc_freq = defaultdict(int)  # 文档频率
    term_freq = defaultdict(int)  # 词频
    total_docs = len(documents)

    for doc in documents:
        words_in_doc = set()
        for word in doc:
            term_freq[word] += 1
            words_in_doc.add(word)

        for word in words_in_doc:
            doc_freq[word] += 1

    # 计算TF-IDF
    tfidf_scores = {}
    for word, tf in term_freq.items():
        # TF = 词频 / 总词数
        tf_score = tf / sum(term_freq.values()) if sum(term_freq.values()) > 0 else 0
        # IDF = log(总文档数 / 包含该词的文档数)
        idf_score = math.log(total_docs / doc_freq[word]) if doc_freq[word] > 0 else 0
        tfidf_scores[word] = tf_score * idf_score

    # 排序并返回top N
    sorted_keywords = sorted(tfidf_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

    return sorted_keywords


def textrank_keyword_extraction(documents, damping=0.85, max_iter=100, top_n=30):
    """
    TextRank关键词抽取

    参数:
        documents: 文档列表
        damping: 阻尼系数
        max_iter: 最大迭代次数
        top_n: 返回top N关键词

    返回:
        textrank_scores: TextRank得分
    """
    print('    [TextRank计算]')

    # 构建词语共现图
    word_graph = defaultdict(lambda: {'score': 1.0, 'neighbors': set()})

    # 窗口大小
    window_size = 3

    for doc in documents:
        words = [w for w in doc if w.strip()]
        for i, word1 in enumerate(words):
            if word1 not in word_graph:
                word_graph[word1]['score'] = 1.0
                word_graph[word1]['neighbors'] = set()

            # 窗口内的其他词
            for j in range(max(0, i - window_size), min(len(words), i + window_size + 1)):
                if i == j:
                    continue
                word2 = words[j]
                word_graph[word1]['neighbors'].add(word2)
                word_graph[word2]['neighbors'].add(word1)

    # TextRank迭代
    for iteration in range(max_iter):
        new_scores = {}

        for word, data in word_graph.items():
            neighbors = data['neighbors']
            if not neighbors:
                new_scores[word] = 0
                continue

            # 计算投票分数
            sum_scores = sum(word_graph[neighbor]['score'] for neighbor in neighbors)
            new_scores[word] = (1 - damping) + damping * sum_scores / len(neighbors)

        # 更新分数
        max_diff = 0
        for word in word_graph:
            diff = abs(new_scores[word] - word_graph[word]['score'])
            word_graph[word]['score'] = new_scores[word]
            max_diff = max(max_diff, diff)

        # 收敛判断
        if max_diff < 0.0001:
            print(f'        TextRank收敛于第{iteration + 1}次迭代')
            break

    # 排序并返回top N
    sorted_keywords = sorted(
        [(word, data['score']) for word, data in word_graph.items()],
        key=lambda x: x[1],
        reverse=True
    )[:top_n]

    return sorted_keywords


def analyze_keywords(danmaku_list):
    """
    分析关键词

    参数:
        danmaku_list: 弹幕列表

    返回:
        keyword_analysis: 关键词分析结果
    """
    print('\n[关键词抽取分析]')

    # 分词
    print('    [分词处理]')
    documents = []
    for d in danmaku_list:
        content = d.get('content', '')
        words = segment_text(content)
        if words:
            documents.append(words)

    print(f'        处理文档数: {len(documents)}')

    # TF-IDF关键词
    tfidf_keywords = tfidf_keyword_extraction(documents, top_n=50)

    # TextRank关键词
    textrank_keywords = textrank_keyword_extraction(documents, top_n=50)

    # 融合两种方法的结果
    # 给予两种方法相同权重，取并集后按综合得分排序
    all_keywords = {}
    for word, score in tfidf_keywords:
        all_keywords[word] = {'tfidf': score, 'textrank': 0}

    for word, score in textrank_keywords:
        if word in all_keywords:
            all_keywords[word]['textrank'] = score
        else:
            all_keywords[word] = {'tfidf': 0, 'textrank': score}

    # 计算综合得分（归一化后求和）
    tfidf_max = max(s['tfidf'] for s in all_keywords.values()) if all_keywords else 1
    textrank_max = max(s['textrank'] for s in all_keywords.values()) if all_keywords else 1

    for word, scores in all_keywords.items():
        normalized_tfidf = scores['tfidf'] / tfidf_max if tfidf_max > 0 else 0
        normalized_textrank = scores['textrank'] / textrank_max if textrank_max > 0 else 0
        scores['combined'] = (normalized_tfidf + normalized_textrank) / 2

    # 按综合得分排序
    final_keywords = sorted(
        [(word, data['combined'], data['tfidf'], data['textrank'])
         for word, data in all_keywords.items()],
        key=lambda x: x[1],
        reverse=True
    )[:50]

    result = {
        'tfidf_keywords': [{'word': w, 'score': round(s, 6)} for w, s in tfidf_keywords[:30]],
        'textrank_keywords': [{'word': w, 'score': round(s, 6)} for w, s in textrank_keywords[:30]],
        'combined_keywords': [
            {
                'word': w,
                'combined_score': round(combined, 4),
                'tfidf_score': round(tfidf, 6),
                'textrank_score': round(textrank, 6)
            }
            for w, combined, tfidf, textrank in final_keywords
        ]
    }

    # 打印结果
    print(f'\n    TF-IDF Top10:')
    for i, (word, score) in enumerate(tfidf_keywords[:10], 1):
        print(f'        {i}. {word}: {score:.6f}')

    print(f'\n    TextRank Top10:')
    for i, (word, score) in enumerate(textrank_keywords[:10], 1):
        print(f'        {i}. {word}: {score:.6f}')

    print(f'\n    综合 Top10:')
    for i, (word, combined, _, _) in enumerate(final_keywords[:10], 1):
        print(f'        {i}. {word}: {combined:.4f}')

    return result


def main():
    print('=' * 70)
    print('关键词抽取分析')
    print('=' * 70)

    # 加载数据
    print('\n[1] 加载弹幕数据...')
    danmaku_list = load_cleaned_data()
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 分析关键词
    result = analyze_keywords(danmaku_list)

    # 保存结果
    print(f'\n[2] 保存结果...')
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'    结果已保存: {OUTPUT_PATH}')

    print('\n' + '=' * 70)
    print('关键词抽取分析完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    main()
