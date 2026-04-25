// 数据服务层 - 支持动态加载NLP结果
// 从JSON文件异步加载数据，提供统一的数据接口

class DataService {
    constructor(basePath = '') {
        this.basePath = basePath || this.getBasePath();
        this._cache = {};
        this._loaded = false;
    }

    getBasePath() {
        // 保持为空，让相对路径直接相对于HTML文件位置解析
        return '';
    }

    async loadJSON(filename) {
        if (this._cache[filename]) {
            return this._cache[filename];
        }

        const url = this.basePath + filename;
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const data = await response.json();
            this._cache[filename] = data;
            return data;
        } catch (error) {
            console.warn(`Failed to load ${filename}:`, error.message);
            return null;
        }
    }

    // 加载所有数据
    async loadAll() {
        console.log('[DataService] Loading data from:', this.basePath);

        const [
            bilibiliData,
            wordfreqData,
            sentimentData,
            sentimentDistData,
            ldaTopicsData,
            timeDistData,
            userBehaviorData,
            sentimentTrendData,
            danmakuClassifiedData,
            keywordsData,
            cooccurrenceData
        ] = await Promise.all([
            this.loadJSON('../agent1_crawler/bilibili_data.json').catch(() => null),
            this.loadJSON('../agent2_nlp/wordfreq.json').catch(() => null),
            this.loadJSON('../agent2_nlp/sentiment.json').catch(() => null),
            this.loadJSON('../agent2_nlp/sentiment_distribution.json').catch(() => null),
            this.loadJSON('../agent2_nlp/lda_sentiment_topics.json').catch(() => null),
            this.loadJSON('../agent2_nlp/danmaku_time_distribution.json').catch(() => null),
            this.loadJSON('../agent2_nlp/user_behavior.json').catch(() => null),
            this.loadJSON('../agent2_nlp/sentiment_trend.json').catch(() => null),
            this.loadJSON('../agent2_nlp/danmaku_classified.json').catch(() => null),
            this.loadJSON('../agent2_nlp/keywords.json').catch(() => null),
            this.loadJSON('../agent2_nlp/word_cooccurrence.json').catch(() => null)
        ]);

        // 处理视频信息
        const videoInfo = bilibiliData?.video_info || {
            bv_id: 'BV1jEAaz3E6K',
            title: '一个视频搞懂OpenClaw！',
            author: '林亦LYi',
            publish_time: '2026-02-28',
            duration: '9:53',
            view_count: 5181106,
            like_count: 135092,
            coin_count: 33811,
            favorite_count: 111353,
            share_count: 8546,
            reply_count: 3268,
            danmaku_count: 5656
        };

        // 处理词云数据 - 转换格式从 {word, freq} 到 {name, value}
        const rawWordfreq = (wordfreqData?.top_100 || []).map(w => ({
            name: w.word,
            value: w.freq
        }));
        const wordcloudData = this.filterStopwords(rawWordfreq);

        // 处理情感数据
        const sentiment = sentimentData?.stats || {
            total: 3514,
            positive: { count: 1480, ratio: 42.12 },
            negative: { count: 1141, ratio: 32.47 },
            neutral: { count: 893, ratio: 25.41 }
        };

        // 添加pieData用于饼图
        sentiment.pieData = [
            { name: '正面', value: sentiment.positive.count },
            { name: '负面', value: sentiment.negative.count },
            { name: '中性', value: sentiment.neutral.count }
        ];

        // 处理情感分布
        const sentimentDist = sentimentDistData || {
            histogram: [],
            stats: { mean: 0.539, median: 0.522, std: 0.285, min: 0, max: 1, total: 3514 }
        };

        // 处理LDA主题
        const ldaTopics = ldaTopicsData || { positive: { topics: [] }, negative: { topics: [] } };

        // 过滤停用词
        const stopwords = new Set(this.STOPWORDS_LIST);
        if (ldaTopics.positive?.topics) {
            ldaTopics.positive.topics = ldaTopics.positive.topics.map(t => ({
                ...t,
                keywords: (t.keywords || []).filter(k => !stopwords.has(k))
            }));
        }
        if (ldaTopics.negative?.topics) {
            ldaTopics.negative.topics = ldaTopics.negative.topics.map(t => ({
                ...t,
                keywords: (t.keywords || []).filter(k => !stopwords.has(k))
            }));
        }

        // 新增分析数据
        const timeDistribution = timeDistData || null;
        const userBehavior = userBehaviorData || null;
        const sentimentTrend = sentimentTrendData || null;
        const danmakuClassified = danmakuClassifiedData || null;
        const keywords = keywordsData || null;
        const cooccurrence = cooccurrenceData || null;

        // 词频Top20
        const wordFreqData = wordcloudData.slice(0, 20).map(w => ({ word: w.name, freq: w.value }));

        const result = {
            videoInfo,
            wordcloudData,
            wordFreqData,
            sentimentData: sentiment,
            sentimentDistribution: sentimentDist,
            ldaTopics,
            timeDistribution,
            userBehavior,
            sentimentTrend,
            danmakuClassified,
            keywords,
            cooccurrence,
            totalWords: wordfreqData?.total_words || 0,
            uniqueWords: wordfreqData?.unique_words || 0
        };

        this._loaded = true;
        return result;
    }

    filterStopwords(wordList) {
        // 只过滤最常见的无意义词汇，保留更多词用于词云展示
        const minimalStopwords = new Set(['的', '了', '是', '在', '和', '有', '我', '不', '就', '也', '都', '要', '会', '能', '说', '被', '把', '让', '给', '与', '及', '而', '但', '却', '还', '又', '更', '最', '这', '那', '个', '之', '着', '过', '吗', '呢', '吧', '啊', '哦', '嗯', '呀', '啦', '嘛', '哈', '呃', '唉', '哟', '嘿', '哼', '哪', '谁', '什么', '怎么', '一个', '一些', '自己', '什么', '这个', '那个']);
        return wordList.filter(w => !minimalStopwords.has(w.name) && w.name.length > 1);
    }

    // 停用词表
    get STOPWORDS_LIST() {
        return ['$', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '?', '_', '"', '"', '、', '。', '《', '》',
            '一', '一些', '一何', '一切', '一则', '一方面', '一旦', '一来', '一样', '一般', '一转眼', '万一',
            '上', '上下', '下', '不', '不仅', '不但', '不光', '不单', '不只', '不外乎', '不如', '不妨', '不尽',
            '不尽然', '不得', '不怕', '不惟', '不成', '不拘', '不料', '不是', '不比', '不然', '不特', '不独',
            '不管', '不至于', '不若', '不论', '不过', '不问', '与', '与其', '与其说', '与否', '与此同时', '且',
            '且不说', '且说', '两者', '个', '个别', '临', '为', '为了', '为什么', '为何', '为止', '为此', '为着',
            '乃', '乃至', '乃至于', '么', '之', '之一', '之所以', '之类', '乌乎', '乎', '乘', '也', '也好', '也罢',
            '了', '二来', '于', '于是', '于是乎', '云云', '云尔', '些', '亦', '人', '人们', '人家', '什么', '什么样',
            '今', '介于', '仍', '仍旧', '从', '从此', '从而', '他', '他人', '他们', '以', '以上', '以为', '以便',
            '以免', '以及', '以故', '以期', '以来', '以至', '以至于', '以致', '们', '任', '任何', '任凭', '似的',
            '但', '但凡', '但是', '何', '何以', '何况', '何处', '何时', '余外', '作为', '你', '你们', '使', '使得',
            '例如', '依', '依据', '依照', '便于', '俺', '俺们', '倘', '倘使', '倘或', '倘然', '倘若', '借', '假使',
            '假如', '假若', '傥然', '像', '儿', '先不先', '光是', '全体', '全部', '兮', '关于', '其', '其一', '其中',
            '其二', '其他', '其余', '其它', '其次', '具体地说', '具体说来', '兼之', '内', '再', '再其次', '再则',
            '再有', '再者', '再者说', '再说', '冒', '冲', '况且', '几', '几时', '凡', '凡是', '凭', '凭借', '出于',
            '出来', '分别', '则', '则甚', '别', '别人', '别处', '别是', '别的', '别管', '别说', '到', '前后', '前此',
            '前者', '加之', '加以', '即', '即令', '即使', '即便', '即如', '即或', '即若', '却', '去', '又', '又及',
            '及', '及其', '及至', '反之', '反而', '反过来', '反过来说', '受到', '另', '另一方面', '另外', '另悉',
            '只', '只当', '只怕', '只是', '只有', '只消', '只要', '只限', '叫', '叮咚', '可', '可以', '可是', '可见',
            '各', '各个', '各位', '各种', '各自', '同', '同时', '后', '后者', '向', '向使', '向着', '吓', '吗', '否则',
            '吧', '吧哒', '吱', '呀', '呃', '呕', '呗', '呜', '呜呼', '呢', '呵', '呵呵', '呸', '呼哧', '咋', '和',
            '咚', '咦', '咧', '咱', '咱们', '咳', '哇', '哈', '哈哈', '哉', '哎', '哎呀', '哎哟', '哗', '哟', '哦',
            '哩', '哪', '哪个', '哪些', '哪儿', '哪天', '哪年', '哪怕', '哪样', '哪边', '哪里', '哼', '哼唷', '唉',
            '唯有', '啊', '啐', '啥', '啦', '啪达', '啷当', '喂', '喏', '喔唷', '喽', '嗡', '嗡嗡', '嗬', '嗯',
            '嗳', '嘎', '嘎登', '嘘', '嘛', '嘻', '嘿', '嘿嘿', '因', '因为', '因了', '因此', '因着', '因而', '固然',
            '在', '在下', '在于', '地', '基于', '处在', '多', '多么', '多少', '大', '大家', '她', '她们', '好', '如',
            '如上', '如上所述', '如下', '如何', '如其', '如同', '如是', '如果', '如此', '如若', '始而', '孰料', '孰知',
            '宁', '宁可', '宁愿', '宁肯', '它', '它们', '对', '对于', '对待', '对方', '对比', '将', '小', '尔', '尔后',
            '尔尔', '尚且', '就', '就是', '就是了', '就是说', '就算', '就要', '尽', '尽管', '尽管如此', '岂但', '己',
            '已', '已矣', '巴', '巴巴', '并', '并且', '并非', '庶乎', '庶几', '开外', '开始', '归', '归齐', '当', '当地',
            '当然', '当着', '彼', '彼时', '彼此', '往', '待', '很', '得', '得了', '怎', '怎么', '怎么办', '怎么样',
            '怎奈', '怎样', '总之', '总的来看', '总的来说', '总的说来', '总而言之', '恰恰相反', '您', '惟其', '慢说',
            '我', '我们', '或', '或则', '或是', '或曰', '或者', '截至', '所', '所以', '所在', '所幸', '所有', '才',
            '才能', '打', '打从', '把', '抑或', '拿', '按', '按照', '换句话说', '换言之', '据', '据此', '接着', '故',
            '故此', '故而', '旁人', '无', '无宁', '无论', '既', '既往', '既是', '既然', '时候', '是', '是以', '是的',
            '曾', '替', '替代', '最', '有', '有些', '有关', '有及', '有时', '有的', '望', '朝', '朝着', '本', '本人',
            '本地', '本着', '本身', '来', '来着', '来自', '来说', '极了', '果然', '果真', '某', '某个', '某些', '某某',
            '根据', '欤', '正值', '正如', '正巧', '正是', '此', '此地', '此处', '此外', '此时', '此次', '此间', '毋宁',
            '每', '每当', '比', '比及', '比如', '比方', '没奈何', '沿', '沿着', '漫说', '焉', '然则', '然后', '然而',
            '照', '照着', '犹且', '犹自', '甚且', '甚么', '甚或', '甚而', '甚至', '甚至于', '用', '用来', '由', '由于',
            '由是', '由此', '由此可见', '的', '的确', '的话', '直到', '相对而言', '省得', '看', '眨眼', '着', '着呢',
            '矣', '矣乎', '矣哉', '离', '竟而', '第', '等', '等到', '等等', '简言之', '管', '类如', '紧接着', '纵',
            '纵令', '纵使', '纵然', '经', '经过', '结果', '给', '继之', '继后', '继而', '综上所述', '罢了', '者', '而',
            '而且', '而况', '而后', '而外', '而已', '而是', '而言', '能', '能否', '腾', '自', '自个儿', '自从', '自各儿',
            '自后', '自家', '自己', '自打', '自身', '至', '至于', '至今', '至若', '致', '般的', '若', '若夫', '若是',
            '若果', '若非', '莫不然', '莫如', '莫若', '虽', '虽则', '虽然', '虽说', '被', '要', '要不', '要不是',
            '要不然', '要么', '要是', '譬喻', '譬如', '让', '许多', '论', '设使', '设或', '设若', '诚如', '诚然', '该',
            '说来', '诸', '诸位', '诸如', '谁', '谁人', '谁料', '知', '贼死', '赖以', '赶', '起', '起见', '趁', '趁着',
            '越是', '距', '跟', '较', '较之', '边', '过', '还', '还是', '还有', '还要', '这', '这一来', '这个', '这么',
            '这么些', '这么样', '这么点儿', '这些', '这会儿', '这儿', '这就是说', '这时', '这样', '这次', '这般', '这边',
            '这里', '进而', '连', '连同', '逐步', '通过', '遵循', '遵照', '那', '那个', '那么', '那么些', '那么样', '那些',
            '那会儿', '那儿', '那时', '那样', '那般', '那边', '那里', '都', '鄙人', '鉴于', '针对', '阿', '除', '除了',
            '除外', '除开', '除此之外', '除非', '随', '随后', '随时', '随着', '难道说', '非但', '非徒', '非特', '非独',
            '靠', '顺', '顺着', '首先', '！', '，', '：', '；', '？', '有点', '好像', '估计', '直接', '不能', '不行'
        ];
    }
}

// 全局数据服务实例
const dataService = new DataService();

// 兼容旧接口 - 保留原有数据结构用于无动态加载的情况
const STOPWORDS = new Set(['$','0','1','2','3','4','5','6','7','8','9','?','_','"','"','、','。','《','》','一','一些','一何','一切','一则','一方面','一旦','一来','一样','一般','一转眼','万一','上','上下','下','不','不仅','不但','不光','不单','不只','不外乎','不如','不妨','不尽','不尽然','不得','不怕','不惟','不成','不拘','不料','不是','不比','不然','不特','不独','不管','不至于','不若','不论','不过','不问','与','与其','与其说','与否','与此同时','且','且不说','且说','两者','个','个别','临','为','为了','为什么','为何','为止','为此','为着','乃','乃至','乃至于','么','之','之一','之所以','之类','乌乎','乎','乘','也','也好','也罢','了','二来','于','于是','于是乎','云云','云尔','些','亦','人','人们','人家','什么','什么样','今','介于','仍','仍旧','从','从此','从而','他','他人','他们','以','以上','以为','以便','以免','以及','以故','以期','以来','以至','以至于','以致','们','任','任何','任凭','似的','但','但凡','但是','何','何以','何况','何处','何时','余外','作为','你','你们','使','使得','例如','依','依据','依照','便于','俺','俺们','倘','倘使','倘或','倘然','倘若','借','假使','假如','假若','傥然','像','儿','先不先','光是','全体','全部','兮','关于','其','其一','其中','其二','其他','其余','其它','其次','具体地说','具体说来','兼之','内','再','再其次','再则','再有','再者','再者说','再说','冒','冲','况且','几','几时','凡','凡是','凭','凭借','出于','出来','分别','则','则甚','别','别人','别处','别是','别的','别管','别说','到','前后','前此','前者','加之','加以','即','即令','即使','即便','即如','即或','即若','却','去','又','又及','及','及其','及至','反之','反而','反过来','反过来说','受到','另','另一方面','另外','另悉','只','只当','只怕','只是','只有','只消','只要','只限','叫','叮咚','可','可以','可是','可见','各','各个','各位','各种','各自','同','同时','后','后者','向','向使','向着','吓','吗','否则','吧','吧哒','吱','呀','呃','呕','呗','呜','呜呼','呢','呵','呵呵','呸','呼哧','咋','和','咚','咦','咧','咱','咱们','咳','哇','哈','哈哈','哉','哎','哎呀','哎哟','哗','哟','哦','哩','哪','哪个','哪些','哪儿','哪天','哪年','哪怕','哪样','哪边','哪里','哼','哼唷','唉','唯有','啊','啐','啥','啦','啪达','啷当','喂','喏','喔唷','喽','嗡','嗡嗡','嗬','嗯','嗳','嘎','嘎登','嘘','嘛','嘻','嘿','嘿嘿','因','因为','因了','因此','因着','因而','固然','在','在下','在于','地','基于','处在','多','多么','多少','大','大家','她','她们','好','如','如上','如上所述','如下','如何','如其','如同','如是','如果','如此','如若','始而','孰料','孰知','宁','宁可','宁愿','宁肯','它','它们','对','对于','对待','对方','对比','将','小','尔','尔后','尔尔','尚且','就','就是','就是了','就是说','就算','就要','尽','尽管','尽管如此','岂但','己','已','已矣','巴','巴巴','并','并且','并非','庶乎','庶几','开外','开始','归','归齐','当','当地','当然','当着','彼','彼时','彼此','往','待','很','得','得了','怎','怎么','怎么办','怎么样','怎奈','怎样','总之','总的来看','总的来说','总的说来','总而言之','恰恰相反','您','惟其','慢说','我','我们','或','或则','或是','或曰','或者','截至','所','所以','所在','所幸','所有','才','才能','打','打从','把','抑或','拿','按','按照','换句话说','换言之','据','据此','接着','故','故此','故而','旁人','无','无宁','无论','既','既往','既是','既然','时候','是','是以','是的','曾','替','替代','最','有','有些','有关','有及','有时','有的','望','朝','朝着','本','本人','本地','本着','本身','来','来着','来自','来说','极了','果然','果真','某','某个','某些','某某','根据','欤','正值','正如','正巧','正是','此','此地','此处','此外','此时','此次','此间','毋宁','每','每当','比','比及','比如','比方','没奈何','沿','沿着','漫说','焉','然则','然后','然而','照','照着','犹且','犹自','甚且','甚么','甚或','甚而','甚至','甚至于','用','用来','由','由于','由是','由此','由此可见','的','的确','的话','直到','相对而言','省得','看','眨眼','着','着呢','矣','矣乎','矣哉','离','竟而','第','等','等到','等等','简言之','管','类如','紧接着','纵','纵令','纵使','纵然','经','经过','结果','给','继之','继后','继而','综上所述','罢了','者','而','而且','而况','而后','而外','而已','而是','而言','能','能否','腾','自','自个儿','自从','自各儿','自后','自家','自己','自打','自身','至','至于','至今','至若','致','般的','若','若夫','若是','若果','若非','莫不然','莫如','莫若','虽','虽则','虽然','虽说','被','要','要不','要不是','要不然','要么','要是','譬喻','譬如','让','许多','论','设使','设或','设若','诚如','诚然','该','说来','诸','诸位','诸如','谁','谁人','谁料','知','贼死','赖以','赶','起','起见','趁','趁着','越是','距','跟','较','较之','边','过','还','还是','还有','还要','这','这一来','这个','这么','这么些','这么样','这么点儿','这些','这会儿','这儿','这就是说','这时','这样','这次','这般','这边','这里','进而','连','连同','逐步','通过','遵循','遵照','那','那个','那么','那么些','那么样','那些','那会儿','那儿','那时','那样','那般','那边','那里','都','鄙人','鉴于','针对','阿','除','除了','除外','除开','除此之外','除非','随','随后','随时','随着','难道说','非但','非徒','非特','非独','靠','顺','顺着','首先','！','，','：','；','？','有点','好像','估计','直接','不能','不行']);

// 原有硬编码数据（保留作为备用）
const videoInfo = {
    bv_id: 'BV1jEAaz3E6K',
    title: '一个视频搞懂OpenClaw！',
    author: '林亦LYi',
    publish_time: '2026-02-28',
    duration: '9:53',
    view_count: 5181106,
    like_count: 135092,
    coin_count: 33811,
    favorite_count: 111353,
    share_count: 8546,
    reply_count: 3268,
    danmaku_count: 5656
};

const _rawWordcloudData = [
    {name: 'AI', value: 142}, {name: 'ai', value: 121}, {name: '一个', value: 93},
    {name: '权限', value: 93}, {name: '问题', value: 87}, {name: 'token', value: 83},
    {name: '豆包', value: 76}, {name: '模型', value: 71}, {name: '手机', value: 67},
    {name: '人类', value: 64}, {name: '智能', value: 58}, {name: '电脑', value: 54},
    {name: '现在', value: 52}, {name: '上下文', value: 49}, {name: '不能', value: 46},
    {name: '直接', value: 44}, {name: '东西', value: 44}, {name: '任务', value: 44},
    {name: '知道', value: 44}, {name: '安全', value: 40}, {name: '需要', value: 40},
    {name: '学习', value: 39}, {name: '感觉', value: 39}, {name: '已经', value: 37},
    {name: '不会', value: 35}, {name: '有点', value: 34}, {name: '老师', value: 33},
    {name: '指令', value: 33}, {name: '危险', value: 32}, {name: '龙虾', value: 31},
    {name: '没有', value: 31}, {name: '病毒', value: 30}, {name: '天网', value: 30},
    {name: 'skill', value: 30}, {name: '世界', value: 29}, {name: 'skills', value: 29},
    {name: '进化', value: 28}, {name: '工具', value: 27}, {name: '哈哈哈哈', value: 27},
    {name: 'cookie', value: 27}, {name: '代码', value: 26}, {name: 'openclaw', value: 26},
    {name: '软件', value: 25}, {name: '能力', value: 25}, {name: '小龙虾', value: 25},
    {name: '隐私', value: 24}, {name: '一下', value: 23}, {name: '使用', value: 23},
    {name: '信息', value: 23}, {name: '记忆', value: 23}, {name: '不行', value: 22},
    {name: '维斯', value: 22}, {name: '工作', value: 22}, {name: '风险', value: 20},
    {name: '赛博', value: 20}, {name: '重要', value: 20}, {name: '接入', value: 20},
    {name: '解决', value: 20}, {name: '阿弥陀佛', value: 20}, {name: '确实', value: 19},
    {name: '之前', value: 19}, {name: '未来', value: 19}, {name: '木马', value: 19},
    {name: '以后', value: 19}, {name: '这是', value: 19}, {name: '图片', value: 19},
    {name: '消耗', value: 19}, {name: '调用', value: 19}, {name: '视频', value: 19},
    {name: '时代', value: 18}, {name: '完全', value: 18}, {name: '机器人', value: 18},
    {name: '故事', value: 18}, {name: '操作', value: 18}, {name: '过程', value: 18},
    {name: '只能', value: 18}, {name: '完成', value: 18}, {name: '就行了', value: 18},
    {name: '文件', value: 18}, {name: '执行', value: 18}, {name: '不够', value: 17},
    {name: '有人', value: 17}, {name: '吓人', value: 17}, {name: '类似', value: 17},
    {name: '大人', value: 17}, {name: '可怕', value: 17}, {name: '一步', value: 17},
    {name: '算力', value: 17}, {name: '数据', value: 16}, {name: '整理', value: 16},
    {name: '卡卡', value: 16}, {name: '提示', value: 16}, {name: '自动', value: 16},
    {name: '好像', value: 15}, {name: '以前', value: 15}, {name: '奥创', value: 15},
    {name: '目前', value: 15}, {name: '爆炸', value: 15}, {name: '密码', value: 15},
    {name: '开源', value: 15}
];

const wordcloudData = _rawWordcloudData.filter(w => !STOPWORDS.has(w.name));
const wordFreqData = wordcloudData.slice(0, 20).map(w => ({word: w.name, freq: w.value}));

const sentimentData = {
    total: 3514,
    positive: {count: 1480, ratio: 42.12},
    negative: {count: 1141, ratio: 32.47},
    neutral: {count: 893, ratio: 25.41},
    pieData: [
        {name: '正面', value: 1480},
        {name: '负面', value: 1141},
        {name: '中性', value: 893}
    ]
};

const sentimentDistribution = {
    histogram: [
        {range: '0.00-0.05', count: 134}, {range: '0.05-0.10', count: 143},
        {range: '0.10-0.15', count: 125}, {range: '0.15-0.20', count: 146},
        {range: '0.20-0.25', count: 160}, {range: '0.25-0.30', count: 140},
        {range: '0.30-0.35', count: 146}, {range: '0.35-0.40', count: 147},
        {range: '0.40-0.45', count: 148}, {range: '0.45-0.50', count: 401},
        {range: '0.50-0.55', count: 188}, {range: '0.55-0.60', count: 156},
        {range: '0.60-0.65', count: 163}, {range: '0.65-0.70', count: 154},
        {range: '0.70-0.75', count: 162}, {range: '0.75-0.80', count: 146},
        {range: '0.80-0.85', count: 175}, {range: '0.85-0.90', count: 209},
        {range: '0.90-0.95', count: 201}, {range: '0.95-1.00', count: 270}
    ],
    stats: {
        mean: 0.539, median: 0.522, std: 0.285, min: 0, max: 1, total: 3514
    }
};

const _rawLdaTopics = {
    positive: {
        danmaku_count: 1099, topic_count: 4, coherence_score: 0.6908,
        topics: [
            {topic_id: 1, keywords: ['人类', '模型', '问题', '能力', '监管', 'AI', '公司', '隐私', '解决', '技术']},
            {topic_id: 2, keywords: ['进化', '可能', '可爱', '奶茶', '记忆', '感觉', '企业', '故事', '智能', '时代']},
            {topic_id: 3, keywords: ['权限', '老师', '工具', '信息', '风险', '重要', '任务', '创造性', '视频', '弹幕']},
            {topic_id: 4, keywords: ['学习', '豆包', '世界', '大人', '手机', '算法', '电脑', '确实', '数据', '危机']}
        ]
    },
    negative: {
        danmaku_count: 848, topic_count: 4, coherence_score: 0.7109,
        topics: [
            {topic_id: 1, keywords: ['漏洞', '后门', '炒作', '咋办', '任务', '风险', '豆包', '智能', '算力', '链接']},
            {topic_id: 2, keywords: ['问题', '不会', '感觉', '病毒', '间谍', '审核', '可怕', '嘴炮', '污染', '像是']},
            {topic_id: 3, keywords: ['电脑', '软件', '权限', '接入', '知道', '消耗', '过程', '使用', '手机', '监控']},
            {topic_id: 4, keywords: ['病毒', '安全', '诈骗', '发现', '赚钱', '觉醒', '整合', '系统', '信息', '主人']}
        ]
    }
};

const ldaTopics = {
    positive: {
        ..._rawLdaTopics.positive,
        topics: _rawLdaTopics.positive.topics.map(t => ({
            ...t,
            keywords: t.keywords.filter(k => !STOPWORDS.has(k))
        }))
    },
    negative: {
        ..._rawLdaTopics.negative,
        topics: _rawLdaTopics.negative.topics.map(t => ({
            ...t,
            keywords: t.keywords.filter(k => !STOPWORDS.has(k))
        }))
    }
};

// 默认数据Promise（同步）
const dataPromise = Promise.resolve({
    wordcloudData,
    wordFreqData,
    totalWords: 10805,
    uniqueWords: 3971,
    sentimentData,
    sentimentDistribution,
    ldaTopics,
    danmakuClassified: {
        total_danmaku: 3515,
        type_distribution: {
            normal: { count: 2305, ratio: 65.58 },
            question: { count: 496, ratio: 14.11 },
            learn: { count: 99, ratio: 2.82 },
            meme: { count: 97, ratio: 2.76 },
            exclaim: { count: 419, ratio: 11.92 },
            spam: { count: 47, ratio: 1.34 },
            bless: { count: 4, ratio: 0.11 },
            idol: { count: 24, ratio: 0.68 },
            negative: { count: 24, ratio: 0.68 }
        },
        top_types: [
            { type: 'normal', label: '普通类', count: 2305, ratio: 65.58, sample_danmaku: [{ content: '新时代的淘金热和卖铲子' }] },
            { type: 'question', label: '提问类', count: 496, ratio: 14.11, sample_danmaku: [{ content: '你不了解他，你就去用他' }] },
            { type: 'exclaim', label: '感叹类', count: 419, ratio: 11.92, sample_danmaku: [{ content: '拔电源啊' }] },
            { type: 'learn', label: '学习类', count: 99, ratio: 2.82, sample_danmaku: [{ content: '每次像这个软件提问' }] },
            { type: 'meme', label: '玩梗类', count: 97, ratio: 2.76, sample_danmaku: [{ content: '哈哈' }] },
            { type: 'spam', label: '刷屏类', count: 47, ratio: 1.34, sample_danmaku: [{ content: '打卡' }] },
            { type: 'idol', label: '追星类', count: 24, ratio: 0.68, sample_danmaku: [{ content: '爱弥斯' }] },
            { type: 'negative', label: '负面类', count: 24, ratio: 0.68, sample_danmaku: [{ content: '个人认为这玩意又是一泡沫' }] },
            { type: 'bless', label: '祝福类', count: 4, ratio: 0.11, sample_danmaku: [{ content: '加油使劲庞氏' }] }
        ]
    },
    userBehavior: {
        total_unique_users: 2156,
        total_danmaku: 3514,
        avg_danmaku_per_user: 1.63,
        highly_active_user_count: 312,
        top20_active_users: [
            { user_id: '用户A', danmaku_count: 15 },
            { user_id: '用户B', danmaku_count: 12 },
            { user_id: '用户C', danmaku_count: 10 }
        ]
    }
});

// 词云点击回调 - 显示包含该词的弹幕
function onWordClick(word, value) {
    console.log('Word clicked:', word, value);
    showRelatedDanmaku(word);
}

// 显示包含关键词的弹幕
function showRelatedDanmaku(word) {
    const panel = document.getElementById('danmaku-detail-panel');
    if (!panel) return;

    panel.classList.add('active');
    panel.querySelector('.detail-title').textContent = `包含"${word}"的弹幕`;

    // 模拟数据 - 实际应从加载的弹幕数据中筛选
    const relatedDanmaku = [
        { content: `这条弹幕包含关键词${word}...`, time: '1:23' },
        { content: `另一个例子${word}在这里`, time: '2:45' },
        { content: `看看这个${word}的效果`, time: '3:12' }
    ];

    const list = panel.querySelector('.detail-list');
    list.innerHTML = relatedDanmaku.map(d =>
        `<div class="detail-item"><span class="time">${d.time}</span><span class="content">${d.content}</span></div>`
    ).join('');
}

// 关闭详情面板
function closeDetailPanel() {
    const panel = document.getElementById('danmaku-detail-panel');
    if (panel) {
        panel.classList.remove('active');
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { dataService, dataPromise, videoInfo };
}
