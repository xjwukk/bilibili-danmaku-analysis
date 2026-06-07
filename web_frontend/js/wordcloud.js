// 词云组件 - 基于 ECharts wordcloud

class WordCloudChart {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            width: options.width || 800,
            height: options.height || 400,
            shape: options.shape || 'circle',
            colorScheme: options.colorScheme || 'default',
            ...options
        };
        this.chart = null;
        this.init();
    }

    init() {
        if (!this.container) {
            console.error('Container not found:', this.container);
            return;
        }
    }

    getColorScheme() {
        const schemes = {
            default: ['#1E40AF', '#3B82F6', '#60A5FA', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4'],
            rainbow: ['#ff0000', '#ff7f00', '#ffff00', '#00ff00', '#0000ff', '#4b0082', '#9400d3'],
            ocean: ['#001f3f', '#0074D9', '#7FDBFF', '#39CCCC', '#01FF70', '#B10DC9', '#FF4136'],
            fire: ['#FF4500', '#FF6347', '#FF7F50', '#FFA07A', '#FFD700', '#FF8C00', '#FF6914'],
            forest: ['#2ecc71', '#27ae60', '#1e8449', '#145a32', '#0a3d2e', '#051f1a']
        };
        return schemes[this.colorScheme] || schemes.default;
    }

    render(data) {
        const colors = this.getColorScheme();

        const option = {
            tooltip: {
                show: true,
                backgroundColor: 'rgba(50, 50, 50, 0.8)',
                borderRadius: 5,
                padding: [10, 15],
                textStyle: { color: '#fff', fontFamily: 'KaiTi, 楷体, STKaiti, SimSun, 宋体, serif' },
                formatter: function(params) {
                    return `<div style="font-size: 14px;">
                        <strong>${params.name}</strong><br/>
                        出现次数: <span style="color: #fac858;">${params.value}</span> 次
                    </div>`;
                }
            },
            series: [{
                type: 'wordCloud',
                sizeRange: [14, 60],
                rotationRange: [-45, 45],
                rotationStep: 15,
                shape: this.options.shape,
                width: this.options.width - 40,
                height: this.options.height - 60,
                left: 'center',
                top: 'center',
                drawOutOfBound: false,
                textStyle: {
                    fontFamily: 'KaiTi, 楷体, STKaiti, SimSun, 宋体, serif',
                    fontWeight: 'bold',
                    color: function() {
                        return colors[Math.floor(Math.random() * colors.length)];
                    }
                },
                emphasis: {
                    textStyle: {
                        shadowBlur: 10,
                        shadowColor: '#333'
                    }
                },
                data: data.map(item => ({
                    name: item.name,
                    value: item.value
                }))
            }]
        };

        // 使用 echarts 渲染
        if (typeof echarts !== 'undefined') {
            this.chart = echarts.init(this.container);
            this.chart.setOption(option);

            // 点击事件
            this.chart.on('click', function(params) {
                console.log('Clicked word:', params.name, 'Value:', params.value);
                if (typeof showRelatedDanmaku === 'function') {
                    showRelatedDanmaku(params.name);
                }
            });

            // 响应式
            window.addEventListener('resize', () => {
                if (this.chart) {
                    this.chart.resize();
                }
            });
        } else {
            console.error('ECharts is not loaded');
        }
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

// 词云点击回调函数
function onWordClick(word, value) {
    console.log('Word clicked:', word, value);
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WordCloudChart;
}