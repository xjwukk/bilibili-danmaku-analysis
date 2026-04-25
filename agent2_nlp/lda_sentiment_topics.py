# -*- coding: utf-8 -*-
"""
LDA主题分析 - 分别对积极和消极弹幕进行主题提取
积极弹幕: SnowNLP情感得分 > 0.7
消极弹幕: SnowNLP情感得分 < 0.3
"""

import json
import os
import re
import jieba
from collections import Counter
from snownlp import SnowNLP

# ============================================================
# 配置路径
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
STOPWORDS_FILE = os.path.join(NLP_DIR, 'cn_stopwords.txt')

# 加载停用词
STOPWORDS = set()
if os.path.exists(STOPWORDS_FILE):
    with open(STOPWORDS_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            word = line.strip()
            if word and not word.startswith('$'):
                STOPWORDS.add(word)
STOPWORDS.update({'2333', '233', '666', '哈哈哈', '笑死', '真的'})


def load_stopwords():
    return STOPWORDS


def filter_content_words(text):
    """只保留名词、动词、形容词"""
    import jieba.posseg as pseg
    words = pseg.cut(text)
    return [w.word for w in words if w.flag in ('n', 'v', 'a', 'an', 'vn', 'ad', 'vd') and len(w.word) > 1]


def prepare_texts(danmaku_list, use_pos_filter=False):
    """预处理弹幕文本"""
    texts = []
    for item in danmaku_list:
        content = item['content']
        if use_pos_filter:
            words = filter_content_words(content)
        else:
            words = jieba.cut(content)
        # 过滤停用词
        filtered = [w for w in words if len(w) > 1 and w not in STOPWORDS
                   and not re.match(r'^[\d\s.,%]+$', w)]
        if filtered:
            texts.append(filtered)
    return texts


def train_lda(texts, num_topics=4, random_state=42):
    """训练LDA模型"""
    from gensim import corpora
    from gensim.models import LdaModel, CoherenceModel

    if len(texts) < num_topics:
        return None, None, None

    # 创建词典和语料库
    dictionary = corpora.Dictionary(texts)
    dictionary.filter_extremes(no_below=2, no_above=0.8)
    corpus = [dictionary.doc2bow(text) for text in texts]

    # 训练LDA模型
    lda_model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        random_state=random_state,
        update_every=1,
        chunksize=100,
        passes=10,
        alpha='auto',
        eta='auto',
    )

    # 计算coherence score
    coherence_model = CoherenceModel(
        model=lda_model, texts=texts, dictionary=dictionary, coherence='c_v'
    )

    return lda_model, dictionary, coherence_model.get_coherence()


def find_optimal_topics(texts, min_topics=3, max_topics=8):
    """寻找最优主题数"""
    from gensim import corpora
    from gensim.models import LdaModel, CoherenceModel

    if len(texts) < max_topics:
        max_topics = max(3, len(texts))

    dictionary = corpora.Dictionary(texts)
    dictionary.filter_extremes(no_below=2, no_above=0.8)
    corpus = [dictionary.doc2bow(text) for text in texts]

    coherence_scores = []
    for num_topics in range(min_topics, max_topics + 1):
        lda = LdaModel(
            corpus=corpus, id2word=dictionary, num_topics=num_topics,
            random_state=42, passes=5
        )
        coherence = CoherenceModel(model=lda, texts=texts, dictionary=dictionary, coherence='c_v')
        score = coherence.get_coherence()
        coherence_scores.append((num_topics, score))
        print(f'        主题数{num_topics}: coherence={score:.4f}')

    best_num = max(coherence_scores, key=lambda x: x[1])[0]
    best_score = max(coherence_scores, key=lambda x: x[1])[1]
    return best_num, best_score, coherence_scores


def analyze_sentiment_danmakus():
    """分析积极和消极弹幕的LDA主题"""
    print('=' * 70)
    print('LDA主题分析 - 积极/消极弹幕分离')
    print('=' * 70)

    # 1. 加载弹幕
    print('\n[1] 加载弹幕数据...')
    with open(os.path.join(NLP_DIR, 'cleaned_danmaku.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    danmaku_list = data['danmaku_list']
    print(f'    弹幕总数: {len(danmaku_list)}')

    # 消极高频词列表（积极弹幕需排除）
    negative_words = {'危险', '病毒', '木马', '恐怖', '恐惧', '不行', '垃圾', '废物', '弱', '烂', '差',
                      '无聊', '尴尬', '无语', '失望', '坑', '恶心', '醉了', '服了', '呵呵', '无奈',
                      '悲剧', '什么鬼', '有毒', '服气', '扯淡', '胡说', '骗人', '没用', '吓人',
                      '污染', '赚钱', '咋办', '嘴炮'}

    # 2. 使用SnowNLP进行情感筛选
    print('\n[2] SnowNLP情感分析...')
    positive_danmakus = []
    negative_danmakus = []

    for item in danmaku_list:
        content = item['content']
        has_neg_word = any(neg_word in content for neg_word in negative_words)
        try:
            s = SnowNLP(content)
            score = s.sentiments
            if score > 0.7 and not has_neg_word:
                positive_danmakus.append(item)
            elif score < 0.3:
                negative_danmakus.append(item)
        except:
            continue

    print(f'    积极弹幕(>0.7且无负面词): {len(positive_danmakus)}条')
    print(f'    消极弹幕(<0.3): {len(negative_danmakus)}条')

    # 保存筛选后的弹幕
    with open(os.path.join(NLP_DIR, 'positive_danmakus.json'), 'w', encoding='utf-8') as f:
        json.dump({'danmaku_list': positive_danmakus}, f, ensure_ascii=False, indent=2)
    with open(os.path.join(NLP_DIR, 'negative_danmakus.json'), 'w', encoding='utf-8') as f:
        json.dump({'danmaku_list': negative_danmakus}, f, ensure_ascii=False, indent=2)

    # 3. 预处理文本
    print('\n[3] 预处理文本...')
    positive_texts = prepare_texts(positive_danmakus, use_pos_filter=True)
    negative_texts = prepare_texts(negative_danmakus, use_pos_filter=True)
    print(f'    积极弹幕有效文档: {len(positive_texts)}')
    print(f'    消极弹幕有效文档: {len(negative_texts)}')

    # 4. 积极弹幕LDA主题分析
    print('\n[4] 积极弹幕LDA主题分析...')
    pos_best_score = 0
    if len(positive_texts) >= 3:
        pos_best_num = 4  # 固定4个主题
        print(f'    使用主题数: {pos_best_num}')

        print(f'    训练LDA模型 (主题数={pos_best_num})...')
        pos_lda, pos_dict, pos_best_score = train_lda(positive_texts, num_topics=pos_best_num)

        print('    积极弹幕主题:')
        pos_topics = []
        for topic_id in range(pos_best_num):
            topic_words = pos_lda.show_topic(topic_id, topn=10)
            words_list = [word for word, prob in topic_words]
            print(f'        主题{topic_id + 1}: {", ".join(words_list[:8])}')
            pos_topics.append({
                'topic_id': topic_id + 1,
                'keywords': words_list,
                'category': 'positive'
            })
    else:
        print('    积极弹幕数量不足，跳过LDA分析')
        pos_topics = []
        pos_best_score = 0

    # 5. 消极弹幕LDA主题分析
    print('\n[5] 消极弹幕LDA主题分析...')
    neg_best_score = 0
    if len(negative_texts) >= 3:
        neg_best_num = 4  # 固定4个主题
        print(f'    使用主题数: {neg_best_num}')

        print(f'    训练LDA模型 (主题数={neg_best_num})...')
        neg_lda, neg_dict, neg_best_score = train_lda(negative_texts, num_topics=neg_best_num)

        print('    消极弹幕主题:')
        neg_topics = []
        for topic_id in range(neg_best_num):
            topic_words = neg_lda.show_topic(topic_id, topn=10)
            words_list = [word for word, prob in topic_words]
            print(f'        主题{topic_id + 1}: {", ".join(words_list[:8])}')
            neg_topics.append({
                'topic_id': topic_id + 1,
                'keywords': words_list,
                'category': 'negative'
            })
    else:
        print('    消极弹幕数量不足，跳过LDA分析')
        neg_topics = []
        neg_best_score = 0

    # 6. 保存结果
    result = {
        'positive': {
            'danmaku_count': len(positive_danmakus),
            'valid_doc_count': len(positive_texts),
            'topic_count': len(pos_topics),
            'coherence_score': round(pos_best_score, 4),
            'topics': pos_topics
        },
        'negative': {
            'danmaku_count': len(negative_danmakus),
            'valid_doc_count': len(negative_texts),
            'topic_count': len(neg_topics),
            'coherence_score': round(neg_best_score, 4),
            'topics': neg_topics
        }
    }

    output_path = os.path.join(NLP_DIR, 'lda_sentiment_topics.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f'\n[6] 结果已保存: {output_path}')

    print('\n' + '=' * 70)
    print('LDA情感主题分析完成!')
    print('=' * 70)

    return result


if __name__ == '__main__':
    analyze_sentiment_danmakus()