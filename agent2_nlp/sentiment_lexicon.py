# -*- coding: utf-8 -*-
"""
专业情感词典加载模块
支持：cnsenti(知网HowNet)、SnowNLP、NTUSD

主要使用cnsenti库的知网HowNet情感词典，约20000+情感词
使用电商评论数据集(online_shopping_10_cats.csv)训练SnowNLP模型
"""

import os

# ============================================================
# 配置
# ============================================================
BASE_DIR = 'F:/Claude project/大数据应用系统开发实践'
NLP_DIR = os.path.join(BASE_DIR, 'agent2_nlp')
LEXICON_DIR = os.path.join(NLP_DIR, 'lexicons')

os.makedirs(LEXICON_DIR, exist_ok=True)

# 否定词列表（用于情感翻转）
NEGATION_WORDS = {
    '不', '没', '无', '别', '非', '否', '莫', '勿', '未',
    '不会', '不能', '不是', '没是', '不需要', '不要', '别要',
    '不太', '不够', '不太', '未', '莫', '非'
}

# 程度修饰词及其权重
INTENSITY_MODIFIERS = {
    '非常': 1.5, '很': 1.3, '特别': 1.5, '极其': 2.0, '超': 1.5,
    '太': 1.5, '真': 1.3, '十分': 1.5, '相当': 1.3,
    '格外': 1.5, '分外': 1.5, '尤为': 1.5, '越发': 1.2,
    '有点': 0.8, '稍微': 0.8, '一点': 0.7, '有些': 0.8,
    '比较': 0.9, '不够': 0.8, '不太': 0.7, '不怎么': 0.7
}


# ============================================================
# 加载停用词表（从cn_stopwords.txt）
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
    # 添加额外空格处理
    stopwords.add(' ')
    stopwords.add('  ')
    print(f'[加载停用词] 共{len(stopwords)}个停用词')
    return stopwords


# ============================================================
# 加载电商评论数据集并训练SnowNLP模型
# ============================================================
def load_shopping_data():
    """加载电商评论数据集"""
    shopping_file = os.path.join(NLP_DIR, 'online_shopping_10_cats.csv')
    if not os.path.exists(shopping_file):
        print('[警告] online_shopping_10_cats.csv不存在，跳过电商评论数据加载')
        return None

    import pandas as pd
    print('[加载电商评论数据集]')
    try:
        df = pd.read_csv(shopping_file)
        print(f'    数据规模: {len(df)}条评论')
        print(f'    类别分布: {df["cat"].value_counts().to_dict()}')
        return df
    except Exception as e:
        print(f'    加载失败: {e}')
        return None


def train_snownlp_model(df):
    """
    使用电商评论数据集训练SnowNLP情感模型

    参考文档：SnowNLP在电商评论场景准确率可达87%
    使用 Sentiment.train(neg_docs, pos_docs) 方法训练
    """
    import random
    import os

    if df is None:
        return None

    print('[训练SnowNLP情感模型]')

    # 准备正面和负面文档列表
    positive_texts = []
    negative_texts = []

    for _, row in df.iterrows():
        review = str(row['review'])
        label = int(row['label'])
        if len(review) > 3 and label in [0, 1]:
            if label == 1:
                positive_texts.append(review)
            else:
                negative_texts.append(review)

    print(f'    正面样本: {len(positive_texts)}条')
    print(f'    负面样本: {len(negative_texts)}条')

    # 创建 Sentiment 对象并训练
    from snownlp.sentiment import Sentiment
    senti = Sentiment()

    # 使用部分数据训练（避免训练时间过长）
    train_pos = positive_texts[:8000]
    train_neg = negative_texts[:8000]

    print('    开始训练...')
    senti.train(train_neg, train_pos)

    # 保存训练后的模型
    model_path = os.path.join(NLP_DIR, 'sentiment_model.marshal')
    senti.save(model_path)
    print(f'    模型已保存: {model_path}')

    # 测试训练后模型的准确率
    print('    测试训练后模型准确率...')
    sample_size = min(500, len(positive_texts), len(negative_texts))
    sampled_pos = random.sample(positive_texts, min(sample_size, len(positive_texts)))
    sampled_neg = random.sample(negative_texts, min(sample_size, len(negative_texts)))

    correct = 0
    for text in sampled_pos:
        try:
            score = senti.classify(text)
            if score > 0.5:  # SnowNLP classify返回负面概率，需要反转
                correct += 1
        except:
            continue
    for text in sampled_neg:
        try:
            score = senti.classify(text)
            if score <= 0.5:
                correct += 1
        except:
            continue

    total_samples = len(sampled_pos) + len(sampled_neg)
    accuracy = correct / total_samples if total_samples > 0 else 0
    print(f'    训练后模型准确率: {accuracy:.2%}')

    class TrainedSnowNLP:
        def __init__(self, senti):
            self.senti = senti

        def run_sentence(self, text):
            """使用训练后的模型分析"""
            try:
                # classify返回负面概率(0=正面, 1=负面)，转换为正面概率
                neg_prob = self.senti.classify(text)
                return 1 - neg_prob
            except:
                return 0.5

    return TrainedSnowNLP(senti)


# ============================================================
# cnsenti 知网HowNet情感词典
# ============================================================
def load_hownet_lexicon():
    """加载cnsenti内置的知网HowNet情感词典"""
    print('[加载知网HowNet情感词典 via cnsenti]')

    from cnsenti import Sentiment
    senti = Sentiment()

    # cnsenti使用内置的HowNet词典，返回pos词和neg词集合
    # 通过测试词来探测词典中的词性
    # 我们直接使用cnsenti的sentiment_count功能

    print('    HowNet词典加载成功（约20000+情感词）')
    return senti


# ============================================================
# SnowNLP情感分析
# ============================================================
def load_snownlp_sentiment():
    """加载SnowNLP情感分析器"""
    print('[加载SnowNLP情感分析器]')

    try:
        from snownlp import SnowNLP
        print('    SnowNLP加载成功')
        return SnowNLP
    except ImportError:
        print('    SnowNLP未安装')
        return None


# ============================================================
# 综合情感分析器
# ============================================================
class SentimentAnalyzer:
    """综合情感分析器，融合多种词典+训练后的SnowNLP模型"""

    def __init__(self):
        print('\n[初始化综合情感分析器]')

        # 加载cnsenti
        self.cnsenti = load_hownet_lexicon()

        # 加载停用词
        self.stopwords = load_stopwords()

        # 加载电商评论数据并训练SnowNLP
        shopping_df = load_shopping_data()
        self.trained_model = train_snownlp_model(shopping_df)
        self.SnowNLP = load_snownlp_sentiment()

        # 额外补充词典（针对弹幕场景）
        self.extra_pos = {
            '实用', '方便', '快捷', '高效', '智能', '专业', '全面',
            '清晰', '详细', '易懂', '靠谱', '良心', '必看', '收藏',
            '转发', '点赞', '打卡', '学习', '厉害', '牛', '棒', '赞',
            '强', '好', '喜欢', '爱', '酷', '帅', '优秀', '精彩',
            '完美', '聪明', '开心', '哈哈', '有趣', '期待', '希望',
            'nb', '牛逼', '绝了', '太棒', '真好', '不错', '神仙'
        }
        self.extra_neg = {
            '危险', '病毒', '木马', '风险', '隐私', '坑爹', '骗人',
            '有毒', '扯淡', '垃圾', '废物', '弱', '烂', '差', '假',
            '烂', '差', '垃圾', '蠢', '傻', '笨', '无聊', '难听',
            '尴尬', '无语', '失望', '坑', '恶心', '醉了', '服了',
            '呵呵', '无奈', '遗憾', '可惜', '悲剧', '什么鬼'
        }

        print(f'    额外正面词: {len(self.extra_pos)}个')
        print(f'    额外负面词: {len(self.extra_neg)}个')
        print(f'    综合情感分析器初始化完成')

    def analyze_cnsenti(self, text):
        """使用cnsenti进行情感分析"""
        result = self.cnsenti.sentiment_count(text)
        return result['pos'], result['neg']

    def analyze_snownlp(self, text):
        """
        使用SnowNLP进行情感分析
        优先使用训练后的模型，其次使用默认模型
        """
        if self.SnowNLP is None:
            return None
        try:
            # 优先使用训练后的模型
            if self.trained_model is not None:
                score = self.trained_model.run_sentence(text)
                return score
            # 回退到默认SnowNLP
            s = self.SnowNLP(text)
            # SnowNLP返回0-1之间的概率，>0.5正面
            return s.sentiments
        except:
            return None

    def analyze_with_lexicon(self, text, pos_words, neg_words):
        """使用词典匹配进行情感分析（分词后匹配）"""
        import jieba

        # 先分词
        words = jieba.cut(text)
        word_list = [w for w in words if w.strip()]

        pos_count = 0
        neg_count = 0

        for word in word_list:
            if word in pos_words:
                pos_count += 1
            if word in neg_words:
                neg_count += 1

        return pos_count, neg_count

    def comprehensive_analyze(self, text):
        """
        综合多种方法的情感分析

        返回:
            sentiment: 'positive', 'negative', 'neutral'
            pos_score: 正面得分
            neg_score: 负面得分
            confidence: 置信度
        """
        import jieba

        # 方法1: cnsenti
        pos1, neg1 = self.analyze_cnsenti(text)

        # 方法2: SnowNLP概率
        snownlp_score = self.analyze_snownlp(text)

        # 方法3: 词典匹配
        words = jieba.cut(text)
        word_list = [w for w in words if w.strip()]

        pos2 = sum(1 for w in word_list if w in self.extra_pos)
        neg2 = sum(1 for w in word_list if w in self.extra_neg)

        # 综合评分
        # cnsenti权重最高
        total_pos = pos1 * 2 + pos2
        total_neg = neg1 * 2 + neg2

        # SnowNLP作为辅助判断
        if snownlp_score is not None:
            if snownlp_score > 0.6:
                total_pos += 1
            elif snownlp_score < 0.4:
                total_neg += 1

        # 判断情感
        if total_pos > total_neg:
            sentiment = 'positive'
            confidence = total_pos / (total_pos + total_neg + 1)
        elif total_neg > total_pos:
            sentiment = 'negative'
            confidence = total_neg / (total_pos + total_neg + 1)
        else:
            sentiment = 'neutral'
            confidence = 0.5

        return {
            'sentiment': sentiment,
            'pos_score': total_pos,
            'neg_score': total_neg,
            'confidence': round(confidence, 3)
        }


def build_combined_lexicon():
    """
    构建综合情感词典（供词典匹配使用）
    返回: (positive_words_set, negative_words_set)
    """
    print('\n[构建综合情感词典]')

    positive_words = set()
    negative_words = set()

    # 添加额外词典
    positive_words.update({
        '实用', '方便', '快捷', '高效', '智能', '专业', '全面',
        '清晰', '详细', '易懂', '靠谱', '良心', '必看', '收藏',
        '转发', '点赞', '打卡', '学习', '厉害', '牛', '棒', '赞',
        '强', '好', '喜欢', '爱', '酷', '帅', '优秀', '精彩',
        '完美', '聪明', '开心', '哈哈', '有趣', '期待', '希望',
        'nb', '牛逼', '绝了', '太棒', '真好', '不错', '神仙',
        '超棒', '超级棒', '碉堡', '炸裂', '太强', '太牛', '佩服',
        '膜拜', '顶', '收藏', '转发', '点赞', '打卡'
    })

    negative_words.update({
        '危险', '病毒', '木马', '风险', '隐私', '坑爹', '骗人',
        '有毒', '扯淡', '垃圾', '废物', '弱', '烂', '差', '假',
        '烂', '差', '垃圾', '蠢', '傻', '笨', '无聊', '难听',
        '尴尬', '无语', '失望', '坑', '恶心', '醉了', '服了',
        '呵呵', '无奈', '遗憾', '可惜', '悲剧', '什么鬼', '有毒',
        '服气', '扯淡', '胡说', '骗人', '坑爹', '弱', '没用'
    })

    print(f'    综合词典规模: 正面{len(positive_words)}个, 负面{len(negative_words)}个')
    return positive_words, negative_words


def get_negation_words():
    return NEGATION_WORDS


def get_intensity_modifiers():
    return INTENSITY_MODIFIERS


# ============================================================
# 验证
# ============================================================
if __name__ == '__main__':
    analyzer = SentimentAnalyzer()

    test_texts = [
        '这个视频太棒了，学到很多！',
        '好开心啊，非常喜欢',
        '垃圾视频，浪费时间',
        '无语了，什么玩意',
        '一般般吧，没什么特别的'
    ]

    print('\n[情感分析测试]')
    for text in test_texts:
        result = analyzer.comprehensive_analyze(text)
        print(f'    "{text}" -> {result["sentiment"]} (pos:{result["pos_score"]}, neg:{result["neg_score"]})')