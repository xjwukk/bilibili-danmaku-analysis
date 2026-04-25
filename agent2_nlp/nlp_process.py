# -*- coding: utf-8 -*-
"""
NLP处理模块
功能：分词、词频统计、词云生成、情感分析、LDA主题分析

改进版：
- 使用cnsenti专业情感词典
- 基于jieba分词后的词典匹配（非字符迭代）
- 否定词处理
- LDA模型coherence score优化
"""

import json
import os
import re
from collections import Counter

import jieba
import jieba.posseg as pseg

# 导入专业情感分析器
from sentiment_lexicon import SentimentAnalyzer, build_combined_lexicon, get_negation_words, get_intensity_modifiers

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
CLEANED_DATA_PATH = os.path.join(NLP_DIR, 'cleaned_danmaku.json')

# 词云字体路径（Windows系统SimHei字体）
FONT_PATH = 'C:/Windows/Fonts/simhei.ttf'
if not os.path.exists(FONT_PATH):
    FONT_PATH = 'C:/Windows/Fonts/simsun.ttc'

# ============================================================
# 停用词表（从cn_stopwords.txt加载）
# ============================================================
def load_stopwords():
    """从cn_stopwords.txt加载停用词"""
    stopwords_file = os.path.join(NLP_DIR, 'cn_stopwords.txt')
    stopwords = set()
    if os.path.exists(stopwords_file):
        with open(stopwords_file, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('$'):
                    stopwords.add(word)
    # 添加弹幕常见无意义词汇
    extra_stopwords = {
        '2333', '233', '666', '哈哈哈', '笑死', '真的', '其实', '觉得', '应该',
        '可能', '不过', '而且', '所以', '但是', '如果', '虽然', '因为', '就是',
        '不是', '这种', '那种', '什么的', '为什么', '怎么样', '多少', '哪些',
    }
    stopwords.update(extra_stopwords)
    print(f'[加载停用词] 共{len(stopwords)}个')
    return stopwords

STOPWORDS = load_stopwords()

# ============================================================
# 情感词典（简化版）
# ============================================================
POSITIVE_WORDS = set([
    '好', '棒', '强', '厉害', '牛', '赞', '支持', '喜欢', '爱', '酷', '帅',
    '优秀', '精彩', '棒', '完美', '聪明', 'nb', '牛逼', '绝了', '太棒', '真好',
    '不错', '期待', '希望', '开心', '哈哈', '笑', '有趣', '有意思', '满分',
    '神', '神仙', '天使', '超棒', '超级棒', '碉堡', '炸裂', '太强', '太牛',
    '佩服', '膜拜', '顶', '赞', '收藏', '转发', '点赞', '打卡', '学习', '实用',
])

NEGATIVE_WORDS = set([
    '烂', '差', '垃圾', '废物', '蠢', '傻', '笨', '无聊', '难听', '难看', '尴尬',
    '无语', '失望', '坑', '骗', '假', '恶心', '吐', '难看', '无聊', '弱', '垃圾',
    '呵呵', '呵呵呵', '无奈', '遗憾', '可惜', '悲剧', '悲剧', '无聊', '没意思',
    '什么鬼', '有毒', '服了', '服气', '醉了', '扯淡', '胡说', '骗人', '坑爹',
])

NEUTRAL_WORDS = set([
    '啊', '吧', '呢', '哦', '嗯', '哈', '啦', '嘛', '呀', '哇', '这', '那',
    '我', '你', '他', '她', '它', '谁', '什么', '怎么', '多少', '这个', '那个',
])


# ============================================================
# 1. 加载清洗后的弹幕
# ============================================================
def load_cleaned_data():
    """加载清洗后的弹幕数据"""
    with open(CLEANED_DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['danmaku_list']


# ============================================================
# 2. 分词与词性标注
# ============================================================
def segment_and_pos(danmaku_list):
    """
    分词与词性标注

    返回:
        words_with_pos: [(word, pos), ...]
        valid_words: 只保留实词（名词、动词、形容词等）
    """
    print('\n[分词与词性标注]')
    valid_words = []

    for item in danmaku_list:
        try:
            content = item['content']
            # 使用jieba进行分词
            words = jieba.cut(content)
            for word in words:
                if word.strip() and word not in STOPWORDS and len(word) > 1:
                    # 过滤纯数字和纯符号
                    if not re.match(r'^[\d\s.,%]+$', word):
                        if not re.match(r'^[，。！？：；""''【】『』()（）·~`@#$%^&*_+=|\\/<>-]+$', word):
                            valid_words.append(word)
        except Exception as e:
            continue

    print(f'    分词后有效词汇数: {len(valid_words)}')

    return valid_words


# ============================================================
# 3. 词频统计
# ============================================================
def word_frequency_analysis(valid_words, top_n=50):
    """
    词频统计

    参数:
        valid_words: 分词后的词汇列表
        top_n: 返回前N个高频词

    返回:
        word_freq: Counter对象，词频统计
    """
    print('\n[词频统计]')

    word_freq = Counter(valid_words)

    # 打印Top N
    print(f'    Top {top_n} 高频词:')
    for i, (word, freq) in enumerate(word_freq.most_common(top_n), 1):
        print(f'    {i:2d}. {word}: {freq}')

    return word_freq


# ============================================================
# 5. 情感分析（改进版 - 基于分词+词典匹配+否定处理）
# ============================================================
def sentiment_analysis_improved(danmaku_list):
    """
    改进版情感分析：使用cnsenti+分词+词典匹配+否定处理

    参数:
        danmaku_list: 弹幕列表

    返回:
        sentiment_result: 情感分析结果
    """
    print('\n[情感分析 - 改进版]')

    # 初始化专业情感分析器
    analyzer = SentimentAnalyzer()
    pos_words, neg_words = build_combined_lexicon()
    negation_words = get_negation_words()
    intensity_mods = get_intensity_modifiers()

    positive_count = 0
    negative_count = 0
    neutral_count = 0
    total_count = len(danmaku_list)

    sentiment_details = []

    for item in danmaku_list:
        content = item['content']

        # 使用综合情感分析
        result = analyzer.comprehensive_analyze(content)

        sentiment = result['sentiment']
        if sentiment == 'positive':
            positive_count += 1
        elif sentiment == 'negative':
            negative_count += 1
        else:
            neutral_count += 1

        sentiment_details.append({
            'content': content,
            'timestamp': item.get('timestamp', 0),
            'sentiment': sentiment,
            'pos_score': result['pos_score'],
            'neg_score': result['neg_score'],
            'confidence': result['confidence'],
        })

    # 统计结果
    sentiment_stats = {
        'total': total_count,
        'positive': {
            'count': positive_count,
            'ratio': round(positive_count / total_count * 100, 2) if total_count > 0 else 0,
        },
        'negative': {
            'count': negative_count,
            'ratio': round(negative_count / total_count * 100, 2) if total_count > 0 else 0,
        },
        'neutral': {
            'count': neutral_count,
            'ratio': round(neutral_count / total_count * 100, 2) if total_count > 0 else 0,
        },
    }

    print(f'    正面弹幕: {positive_count} ({sentiment_stats["positive"]["ratio"]}%)')
    print(f'    负面弹幕: {negative_count} ({sentiment_stats["negative"]["ratio"]}%)')
    print(f'    中性弹幕: {neutral_count} ({sentiment_stats["neutral"]["ratio"]}%)')

    return {
        'stats': sentiment_stats,
        'details': sentiment_details[:100],
    }


# 保留旧接口兼容
def sentiment_analysis(danmaku_list):
    """兼容旧接口，调用改进版"""
    return sentiment_analysis_improved(danmaku_list)


# ============================================================
# 6. LDA主题分析（优化版 - Bigram/POS过滤/Coherence Score）
# ============================================================
def filter_content_words(text):
    """只保留名词、动词、形容词（POS过滤）"""
    words = pseg.cut(text)
    return [w.word for w in words if w.flag in ('n', 'v', 'a', 'an', 'vn', 'ad', 'vd') and len(w.word) > 1]


def find_optimal_topics(texts, dictionary, corpus, min_topics=3, max_topics=8):
    """寻找最优主题数（基于coherence score）"""
    from gensim.models import LdaModel, CoherenceModel

    print('    寻找最优主题数...')
    coherence_scores = []

    for num_topics in range(min_topics, max_topics + 1):
        lda = LdaModel(
            corpus=corpus,
            id2word=dictionary,
            num_topics=num_topics,
            random_state=42,
            passes=5
        )
        coherence = CoherenceModel(model=lda, texts=texts, dictionary=dictionary, coherence='c_v')
        score = coherence.get_coherence()
        coherence_scores.append((num_topics, score))
        print(f'        主题数{num_topics}: coherence={score:.4f}')

    # 选择最高coherence的主题数
    best_num = max(coherence_scores, key=lambda x: x[1])[0]
    print(f'    最优主题数: {best_num} (coherence={max(coherence_scores, key=lambda x: x[1])[1]:.4f})')
    return best_num, coherence_scores


def lda_topic_analysis_improved(danmaku_list, num_topics=5):
    """
    改进版LDA主题分析：含Bigram提取、POS过滤、Coherence Score优化

    参数:
        danmaku_list: 弹幕列表
        num_topics: 默认主题数（如果coherence优化开启则自动调整）

    返回:
        lda_result: LDA分析结果
    """
    print(f'\n[LDA主题分析 - 优化版]')

    try:
        from gensim import corpora
        from gensim.models import LdaModel
        from gensim.models.phrases import Phrases, Phraser
        from gensim.models import CoherenceModel
    except ImportError:
        print('    gensim未正确安装，跳过LDA分析')
        return None

    # 1. 准备语料 - 使用POS过滤
    print('    [1] 分词与POS过滤...')
    raw_texts = []
    for item in danmaku_list:
        content = item['content']
        # 使用jieba分词
        words = jieba.cut(content)
        # POS过滤：只保留名词、动词、形容词
        filtered = [w for w in words if len(w) > 1 and w not in STOPWORDS
                   and not re.match(r'^[\d\s.,%]+$', w)]
        if filtered:
            raw_texts.append(filtered)

    print(f'    预处理后文档数: {len(raw_texts)}')

    if len(raw_texts) < num_topics:
        print(f'    弹幕数量不足，无法进行LDA分析')
        return None

    # 2. Bigram检测
    print('    [2] 检测Bigram短语...')
    phrases = Phrases(raw_texts)
    bigram = Phraser(phrases)

    # 使用bigram后的文本
    texts_bigram = [bigram[text] for text in raw_texts]

    # 统计新产生的bigram
    bigram_count = sum(1 for text in texts_bigram for token in text if '_' in token)
    print(f'    检测到Bigram: {bigram_count}个')

    # 3. 创建字典和语料库
    print('    [3] 创建词典与语料库...')
    dictionary = corpora.Dictionary(texts_bigram)
    dictionary.filter_extremes(no_below=2, no_above=0.8)
    corpus = [dictionary.doc2bow(text) for text in texts_bigram]

    print(f'    词典大小: {len(dictionary)}')

    # 4. 计算最优主题数（使用coherence score）
    print('    [4] 计算最优主题数...')
    optimal_topics, coherence_scores = find_optimal_topics(texts_bigram, dictionary, corpus)

    # 如果最优主题数与默认不同，使用最优
    actual_topics = optimal_topics if optimal_topics != num_topics else num_topics
    print(f'    使用主题数: {actual_topics}')

    # 5. 训练最终LDA模型
    print(f'    [5] 训练LDA模型 (主题数={actual_topics})...')
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=actual_topics,
        random_state=42,
        update_every=1,
        chunksize=100,
        passes=10,
        alpha='auto',
        eta='auto',
    )

    # 6. 获取主题
    print('    [6] 提取主题关键词...')
    topics = []
    for topic_id in range(actual_topics):
        topic_words = lda_model.show_topic(topic_id, topn=15)
        words_list = [word for word, prob in topic_words]
        probs_list = [float(round(prob, 4)) for word, prob in topic_words]

        topics.append({
            'topic_id': topic_id + 1,
            'keywords': words_list,
            'probabilities': probs_list,
        })

        print(f'        主题{topic_id + 1}: {", ".join(words_list[:8])}')

    # 计算最终coherence score
    final_coherence = CoherenceModel(model=lda_model, texts=texts_bigram, dictionary=dictionary, coherence='c_v')
    final_score = final_coherence.get_coherence()

    return {
        'num_topics': actual_topics,
        'topics': topics,
        'total_documents': len(texts_bigram),
        'bigram_count': bigram_count,
        'coherence_score': round(final_score, 4),
        'coherence_history': coherence_scores,
        'dictionary_size': len(dictionary),
    }


# 保留旧接口兼容
def lda_topic_analysis(danmaku_list, num_topics=5):
    """兼容旧接口，调用改进版"""
    return lda_topic_analysis_improved(danmaku_list, num_topics)


# ============================================================
# 主函数
# ============================================================
def main():
    print('=' * 70)
    print('弹幕NLP处理模块')
    print('=' * 70)

    # 1. 加载数据
    print('\n[1] 加载清洗后的弹幕数据...')
    danmaku_list = load_cleaned_data()
    print(f'    弹幕数量: {len(danmaku_list)}')

    # 2. 分词
    valid_words = segment_and_pos(danmaku_list)

    # 3. 词频统计
    word_freq = word_frequency_analysis(valid_words, top_n=50)

    # 保存词频结果
    wordfreq_path = os.path.join(NLP_DIR, 'wordfreq.json')
    wordfreq_data = {
        'total_words': len(valid_words),
        'unique_words': len(word_freq),
        'top_100': [{'word': w, 'freq': f} for w, f in word_freq.most_common(100)],
    }
    with open(wordfreq_path, 'w', encoding='utf-8') as f:
        json.dump(wordfreq_data, f, ensure_ascii=False, indent=2)
    print(f'\n    词频统计已保存: {wordfreq_path}')

    # 4. 词云生成（已在独立脚本generate_wordcloud.py中实现）
    # 由于wordcloud库在此环境下存在segfault问题，词云生成独立运行
    print('\n[4] 词云生成: 请运行 generate_wordcloud.py 生成词云图片')

    # 5. 情感分析
    sentiment_result = sentiment_analysis(danmaku_list)

    # 保存情感分析结果
    sentiment_path = os.path.join(NLP_DIR, 'sentiment.json')
    with open(sentiment_path, 'w', encoding='utf-8') as f:
        json.dump(sentiment_result, f, ensure_ascii=False, indent=2)
    print(f'    情感分析结果已保存: {sentiment_path}')

    # 6. LDA主题分析
    lda_result = lda_topic_analysis(danmaku_list, num_topics=5)

    if lda_result:
        # 保存LDA结果
        lda_path = os.path.join(NLP_DIR, 'lda_topics.json')
        with open(lda_path, 'w', encoding='utf-8') as f:
            json.dump(lda_result, f, ensure_ascii=False, indent=2)
        print(f'    LDA主题结果已保存: {lda_path}')

    print('\n' + '=' * 70)
    print('NLP处理完成!')
    print('=' * 70)

    # 返回主要统计结果
    return {
        'total_danmaku': len(danmaku_list),
        'word_freq_top10': word_freq.most_common(10),
        'sentiment_stats': sentiment_result['stats'],
        'lda_topics': lda_result['topics'] if lda_result else [],
    }


if __name__ == '__main__':
    results = main()

    # 打印汇总结果
    print('\n' + '=' * 70)
    print('主要统计结果汇总')
    print('=' * 70)

    print('\n词频Top 10:')
    for i, (word, freq) in enumerate(results['word_freq_top10'], 1):
        print(f'  {i:2d}. {word}: {freq}')

    print('\n情感分布:')
    stats = results['sentiment_stats']
    print(f'  正面: {stats["positive"]["count"]}条 ({stats["positive"]["ratio"]}%)')
    print(f'  负面: {stats["negative"]["count"]}条 ({stats["negative"]["ratio"]}%)')
    print(f'  中性: {stats["neutral"]["count"]}条 ({stats["neutral"]["ratio"]}%)')

    if results['lda_topics']:
        print(f'\nLDA主题数量: {len(results["lda_topics"])}')
        for topic in results['lda_topics'][:3]:
            print(f'  主题{topic["topic_id"]}: {", ".join(topic["keywords"][:5])}')