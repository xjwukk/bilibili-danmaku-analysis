// 时间轴组件 - 展示弹幕时间分布，支持滑动查看各时段弹幕

class TimelineChart {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            height: options.height || 120,
            bucketSize: options.bucketSize || 60, // 秒
            ...options
        };
        this.chart = null;
        this.currentIndex = 0;
        this.data = [];
        this.init();
    }

    init() {
        if (!this.container) {
            console.error('Timeline container not found');
            return;
        }
    }

    render(data) {
        this.data = data || [];

        if (typeof echarts === 'undefined') {
            console.error('ECharts not loaded');
            return;
        }

        // 准备时间轴数据
        const timeLabels = [];
        const danmakuCounts = [];

        for (const item of this.data) {
            const minutes = Math.floor(item.time_bucket / 60);
            const seconds = item.time_bucket % 60;
            timeLabels.push(`${minutes}:${seconds.toString().padStart(2, '0')}`);
            danmakuCounts.push(item.count);
        }

        if (timeLabels.length === 0) {
            timeLabels.push('0:00');
            danmakuCounts.push(0);
        }

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: {
                    type: 'line',
                    lineStyle: { color: '#3B82F6', width: 2 }
                },
                backgroundColor: 'rgba(30, 64, 175, 0.9)',
                borderRadius: 6,
                padding: [8, 12],
                textStyle: { color: '#fff', fontFamily: 'KaiTi, 楷体, STKaiti, SimSun, serif', fontSize: 12 },
                formatter: function(params) {
                    const idx = params[0].dataIndex;
                    const item = this.data[idx];
                    if (!item) return '';
                    return `<div style="font-size:12px">
                        <strong>${params[0].name}</strong><br/>
                        弹幕数量: <span style="color:#60A5FA">${item.count}</span> 条
                    </div>`;
                }.bind(this)
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
                data: timeLabels,
                axisLabel: {
                    interval: Math.floor(timeLabels.length / 10),
                    rotate: 45,
                    color: '#64748B',
                    fontSize: 10,
                    fontFamily: 'SimSun, serif'
                },
                axisLine: { lineStyle: { color: '#E2E8F0' } },
                axisTick: { show: false }
            },
            yAxis: {
                type: 'value',
                axisLabel: { color: '#64748B', fontSize: 10 },
                axisLine: { show: false },
                splitLine: { lineStyle: { color: '#F1F5F9' } }
            },
            series: [{
                name: '弹幕数量',
                type: 'bar',
                data: danmakuCounts,
                barWidth: '80%',
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#3B82F6' },
                        { offset: 1, color: '#93C5FD' }
                    ]),
                    borderRadius: [2, 2, 0, 0]
                },
                emphasis: {
                    itemStyle: {
                        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                            { offset: 0, color: '#60A5FA' },
                            { offset: 1, color: '#BFDBFE' }
                        ])
                    }
                }
            }],
            dataZoom: [{
                type: 'slider',
                show: true,
                bottom: 0,
                height: 20,
                borderColor: '#E2E8F0',
                fillerColor: 'rgba(59, 130, 246, 0.2)',
                handleStyle: {
                    color: '#3B82F6',
                    borderColor: '#3B82F6'
                },
                textStyle: {
                    color: '#64748B',
                    fontSize: 10
                },
                filterMode: 'filter'
            }, {
                type: 'inside',
                zoomLock: false
            }]
        };

        this.chart = echarts.init(this.container);
        this.chart.setOption(option);

        // 点击某根柱子时高亮并显示详情
        this.chart.on('click', (params) => {
            this.currentIndex = params.dataIndex;
            this.highlightBucket(params.dataIndex);
        });

        window.addEventListener('resize', () => {
            if (this.chart) {
                this.chart.resize();
            }
        });
    }

    highlightBucket(index) {
        if (!this.data || !this.data[index]) return;

        const item = this.data[index];
        const event = new CustomEvent('timelineBucketSelect', {
            detail: {
                timeBucket: item.time_bucket,
                timeLabel: item.time_label || `${Math.floor(item.time_bucket / 60)}:${(item.time_bucket % 60).toString().padStart(2, '0')}`,
                count: item.count
            }
        });
        window.dispatchEvent(event);
    }

    resize() {
        if (this.chart) {
            this.chart.resize();
        }
    }

    dispose() {
        if (this.chart) {
            this.chart.dispose();
            this.chart = null;
        }
    }
}

// 时间轴控制器
class TimelineController {
    constructor() {
        this.currentTime = 0;
        this.isPlaying = false;
        this.playInterval = null;
        this.onTimeChange = null;
    }

    play() {
        if (this.isPlaying) return;
        this.isPlaying = true;

        this.playInterval = setInterval(() => {
            this.currentTime += 1;
            if (this.currentTime > 593) { // 视频时长约9:53
                this.currentTime = 0;
            }
            if (this.onTimeChange) {
                this.onTimeChange(this.currentTime);
            }
        }, 1000);
    }

    pause() {
        this.isPlaying = false;
        if (this.playInterval) {
            clearInterval(this.playInterval);
            this.playInterval = null;
        }
    }

    seek(time) {
        this.currentTime = time;
        if (this.onTimeChange) {
            this.onTimeChange(time);
        }
    }

    dispose() {
        this.pause();
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { TimelineChart, TimelineController };
}
