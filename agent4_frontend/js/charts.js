// 统计图表组件 - 基于 ECharts
// 依赖: echarts, sentimentDistribution (来自 data.js)

class ChartManager {
    constructor() {
        this.charts = {};
    }

    // 初始化所有图表
    initAllCharts(data) {
        this.initWordFreqChart();
        this.initSentimentChart();
        this.initSentimentDistChart();
        this.initSentimentTrendChart();
        this.initDanmakuTypeChart();
        this.initUserBehaviorChart(data);
    }

    // 用户行为统计
    initUserBehaviorChart(data) {
        const userBehavior = data?.userBehavior;
        if (!userBehavior) return;

        document.getElementById('ub-total-users').textContent = (userBehavior.total_unique_users || 0).toLocaleString();
        document.getElementById('ub-avg-danmaku').textContent = (userBehavior.avg_danmaku_per_user || 0).toFixed(2);
        document.getElementById('ub-active-users').textContent = (userBehavior.highly_active_user_count || 0).toLocaleString();

        const topUser = userBehavior.top20_active_users?.[0];
        const topUserId = topUser?.user_id || '匿名用户';
        document.getElementById('ub-top-user').textContent = topUser ? `${topUserId} (${topUser.danmaku_count}条)` : '-';
    }

    // 情感趋势折线图
    initSentimentTrendChart() {
        const container = document.getElementById('sentiment-trend-chart');
        if (!container) return;

        const chart = echarts.init(container);
        this.charts.sentimentTrend = chart;

        // 模拟数据 - 实际应从 sentiment_trend.json 加载
        const trendData = [];
        for (let i = 0; i < 60; i++) {
            trendData.push({
                time_bucket: i * 10,
                time_label: `${Math.floor(i / 6)}:${(i % 6) * 10}`,
                avg_sentiment_score: Math.random() * 0.6 + 0.3,
                danmaku_count: Math.floor(Math.random() * 50) + 10
            });
        }

        const option = {
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(30, 64, 175, 0.9)',
                borderRadius: 6,
                padding: [10, 14],
                textStyle: { color: '#fff', fontFamily: 'KaiTi, 楷体, serif' },
                formatter: function(params) {
                    const idx = params[0].dataIndex;
                    const item = trendData[idx];
                    if (!item) return '';
                    return `<div style="font-size:13px">
                        <strong>${item.time_label}</strong><br/>
                        情感得分: <span style="color:#60A5FA">${item.avg_sentiment_score.toFixed(3)}</span><br/>
                        弹幕数量: <span style="color:#10B981">${item.danmaku_count}</span> 条
                    </div>`;
                }
            },
            legend: {
                data: ['情感得分', '弹幕数量'],
                top: 0,
                textStyle: { color: '#64748B', fontFamily: 'SimSun, serif' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                top: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: trendData.map(d => d.time_label),
                axisLabel: {
                    interval: 9,
                    rotate: 45,
                    color: '#64748B',
                    fontSize: 10,
                    fontFamily: 'SimSun, serif'
                },
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                axisTick: { show: false }
            },
            yAxis: [{
                type: 'value',
                name: '情感得分',
                min: 0,
                max: 1,
                axisLabel: { color: '#64748B', fontSize: 10 },
                axisLine: { show: false },
                splitLine: { lineStyle: { color: '#F1F5F9' } }
            }, {
                type: 'value',
                name: '弹幕数量',
                axisLabel: { color: '#64748B', fontSize: 10 },
                axisLine: { show: false },
                splitLine: { show: false }
            }],
            series: [{
                name: '情感得分',
                type: 'line',
                data: trendData.map(d => d.avg_sentiment_score),
                smooth: true,
                lineStyle: { width: 2, color: '#3B82F6' },
                itemStyle: { color: '#3B82F6' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                        { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
                    ])
                }
            }, {
                name: '弹幕数量',
                type: 'bar',
                yAxisIndex: 1,
                data: trendData.map(d => d.danmaku_count),
                barWidth: '50%',
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#10B981' },
                        { offset: 1, color: '#34D399' }
                    ]),
                    borderRadius: [2, 2, 0, 0]
                }
            }]
        };

        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
    }

    // 弹幕类型分布图
    initDanmakuTypeChart() {
        const container = document.getElementById('danmaku-type-chart');
        if (!container) return;

        const chart = echarts.init(container);
        this.charts.danmakuType = chart;

        // 模拟数据 - 实际应从 danmaku_classified.json 加载
        const typeData = [
            { name: '祝福类', value: 320, itemStyle: { color: '#10B981' } },
            { name: '玩梗类', value: 580, itemStyle: { color: '#F59E0B' } },
            { name: '刷屏类', value: 245, itemStyle: { color: '#3B82F6' } },
            { name: '提问类', value: 180, itemStyle: { color: '#8B5CF6' } },
            { name: '感叹类', value: 420, itemStyle: { color: '#EC4899' } },
            { name: '普通类', value: 1769, itemStyle: { color: '#6B7280' } }
        ];

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: 'rgba(30, 64, 175, 0.9)',
                borderRadius: 6,
                padding: [10, 14],
                textStyle: { color: '#fff', fontFamily: 'KaiTi, serif' },
                formatter: function(params) {
                    return `<div style="font-size:13px">
                        <strong>${params.name}</strong><br/>
                        数量: <span style="color:${params.color}">${params.value}</span> 条<br/>
                        占比: <span style="color:${params.color}">${params.percent.toFixed(1)}%</span>
                    </div>`;
                }
            },
            legend: {
                orient: 'vertical',
                right: '5%',
                top: 'center',
                itemWidth: 14,
                itemHeight: 10,
                textStyle: { color: '#64748B', fontSize: 12, fontFamily: 'SimSun, serif' }
            },
            series: [{
                name: '弹幕类型',
                type: 'pie',
                radius: ['30%', '60%'],
                center: ['40%', '50%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    position: 'outside',
                    formatter: '{b}\n{d}%',
                    color: '#334155',
                    fontSize: 11,
                    fontFamily: 'SimSun, serif'
                },
                labelLine: { show: true, lineStyle: { color: '#CBD5E1' } },
                emphasis: {
                    itemStyle: { shadowBlur: 8, shadowColor: 'rgba(30, 64, 175, 0.3)' }
                },
                data: typeData
            }]
        };

        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
    }

    // 词频统计柱状图 (Top 20)
    initWordFreqChart() {
        const container = document.getElementById('wordfreq-chart');
        if (!container) return;

        const chart = echarts.init(container);
        this.charts.wordfreq = chart;

        const top20Data = wordFreqData.slice(0, 20);
        const xData = top20Data.map(item => item.word);
        const yData = top20Data.map(item => item.freq);

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                backgroundColor: 'rgba(30, 64, 175, 0.9)',
                borderRadius: 6,
                padding: [10, 14],
                textStyle: { color: '#fff', fontFamily: 'KaiTi, 楷体, STKaiti, SimSun, 宋体, serif' },
                formatter: function(params) {
                    const data = params[0];
                    return `<div style="font-size:13px">
                        <strong>${data.name}</strong><br/>
                        出现次数: <span style="color:#FCD34D">${data.value}</span> 次
                    </div>`;
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '22%',
                top: '8%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: xData,
                axisLabel: {
                    interval: 0,
                    rotate: 45,
                    color: '#64748B',
                    fontSize: 11,
                    fontFamily: 'SimSun, 宋体, serif'
                },
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                axisTick: { show: false }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#64748B', fontFamily: 'SimSun, 宋体, serif' },
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                splitLine: { lineStyle: { color: '#F1F5F9' } }
            },
            series: [{
                name: '词频',
                type: 'bar',
                barWidth: '55%',
                data: yData,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#3B82F6' },
                        { offset: 1, color: '#1E40AF' }
                    ]),
                    borderRadius: [4, 4, 0, 0]
                },
                emphasis: {
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#60A5FA' },
                            { offset: 1, color: '#3B82F6' }
                        ])
                    }
                }
            }]
        };

        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
    }

    // 情感分析饼图
    initSentimentChart() {
        const container = document.getElementById('sentiment-chart');
        if (!container) return;

        const chart = echarts.init(container);
        this.charts.sentiment = chart;

        const option = {
            tooltip: {
                trigger: 'item',
                backgroundColor: 'rgba(30, 64, 175, 0.9)',
                borderRadius: 6,
                padding: [10, 14],
                textStyle: { color: '#fff', fontFamily: 'KaiTi, 楷体, STKaiti, SimSun, 宋体, serif' },
                formatter: function(params) {
                    return `<div style="font-size:13px">
                        <strong>${params.name}</strong><br/>
                        数量: <span style="color:${params.color}">${params.value}</span> 条<br/>
                        占比: <span style="color:${params.color}">${params.percent.toFixed(1)}%</span>
                    </div>`;
                }
            },
            legend: {
                orient: 'vertical',
                right: '5%',
                top: 'center',
                itemWidth: 14,
                itemHeight: 10,
                textStyle: { color: '#64748B', fontSize: 12, fontFamily: 'SimSun, 宋体, serif' }
            },
            series: [{
                name: '情感分布',
                type: 'pie',
                radius: ['38%', '65%'],
                center: ['38%', '50%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    position: 'outside',
                    formatter: '{b}\n{d}%',
                    color: '#334155',
                    fontSize: 11,
                    fontFamily: 'SimSun, 宋体, serif'
                },
                labelLine: { show: true, lineStyle: { color: '#CBD5E1' } },
                emphasis: {
                    itemStyle: { shadowBlur: 8, shadowColor: 'rgba(30, 64, 175, 0.3)' }
                },
                data: [
                    { name: '正面', value: sentimentData.positive.count, itemStyle: { color: '#10B981' } },
                    { name: '负面', value: sentimentData.negative.count, itemStyle: { color: '#EF4444' } },
                    { name: '中性', value: sentimentData.neutral.count, itemStyle: { color: '#6B7280' } }
                ]
            }]
        };

        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
    }

    // 情感得分分布直方图 (从 sentiment_distribution.json 读取)
    initSentimentDistChart() {
        const container = document.getElementById('sentiment-dist-chart');
        if (!container) return;

        const chart = echarts.init(container);
        this.charts.sentimentDist = chart;

        const histogram = sentimentDistribution.histogram || [];
        const ranges = histogram.map(d => d.range);
        const counts = histogram.map(d => d.count);

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                backgroundColor: 'rgba(30, 64, 175, 0.9)',
                borderRadius: 6,
                padding: [10, 14],
                textStyle: { color: '#fff', fontFamily: 'KaiTi, 楷体, STKaiti, SimSun, 宋体, serif' },
                formatter: function(params) {
                    const data = params[0];
                    return `<div style="font-size:13px">
                        <strong>${data.name}</strong><br/>
                        弹幕数量: <span style="color:#60A5FA">${data.value}</span> 条
                    </div>`;
                }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '18%',
                top: '8%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: ranges,
                axisLabel: {
                    interval: 2,
                    rotate: 45,
                    color: '#64748B',
                    fontSize: 10,
                    fontFamily: 'SimSun, 宋体, serif'
                },
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                axisTick: { show: false }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#64748B', fontFamily: 'SimSun, 宋体, serif' },
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                splitLine: { lineStyle: { color: '#F1F5F9' } }
            },
            series: [{
                name: '弹幕数量',
                type: 'bar',
                barWidth: '75%',
                data: counts,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#EF4444' },
                        { offset: 0.4, color: '#F59E0B' },
                        { offset: 1, color: '#10B981' }
                    ]),
                    borderRadius: [3, 3, 0, 0]
                },
                emphasis: {
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#F87171' },
                            { offset: 0.4, color: '#FBBF24' },
                            { offset: 1, color: '#34D399' }
                        ])
                    }
                },
                markLine: {
                    silent: true,
                    lineStyle: { color: '#94A3B8', type: 'dashed', width: 1.5 },
                    data: [
                        { xAxis: 8, name: '消极/中性分界 (0.4)' },
                        { xAxis: 12, name: '中性/积极分界 (0.6)' }
                    ],
                    label: {
                        formatter: '{b}',
                        position: 'end',
                        color: '#64748B',
                        fontSize: 10,
                        fontFamily: 'SimSun, 宋体, serif'
                    }
                }
            }]
        };

        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
    }

    // 刷新所有图表
    refreshAll() {
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.resize) chart.resize();
        });
    }

    // 销毁所有图表
    disposeAll() {
        Object.values(this.charts).forEach(chart => {
            if (chart && chart.dispose) chart.dispose();
        });
        this.charts = {};
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartManager;
}
