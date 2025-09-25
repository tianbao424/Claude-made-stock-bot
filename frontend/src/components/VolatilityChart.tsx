import React, { useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, Activity, Info } from 'lucide-react';

interface PriceData {
  date: string;
  price: number;
  volume: number;
}

interface VolatilityPeriod {
  start_date: string;
  end_date: string;
  days: number;
  volatility: number;
  is_sideways: boolean;
}

interface BreakoutPoint {
  date: string;
  price: number;
  direction: 'upward' | 'downward';
  strength: number;
}

interface VolatilityChartProps {
  stockCode: string;
  stockName: string;
  priceData: PriceData[];
  volatilityPeriods: VolatilityPeriod[];
  breakoutPoints: BreakoutPoint[];
  currentAnalysis: {
    sideways_period_days: number;
    has_breakout: boolean;
    breakout_direction: string;
    volatility_score: number;
    pattern_quality: string;
  };
  className?: string;
}

const VolatilityChart: React.FC<VolatilityChartProps> = ({
  stockCode,
  stockName,
  priceData,
  volatilityPeriods,
  breakoutPoints,
  currentAnalysis,
  className = ''
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    drawChart();
  }, [priceData, volatilityPeriods, breakoutPoints]);

  const drawChart = () => {
    const canvas = canvasRef.current;
    const container = chartContainerRef.current;
    if (!canvas || !container || priceData.length === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // 设置画布尺寸
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = 400 * window.devicePixelRatio;
    canvas.style.width = rect.width + 'px';
    canvas.style.height = '400px';
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

    const width = rect.width;
    const height = 400;
    const padding = { top: 40, right: 60, bottom: 60, left: 60 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // 清空画布
    ctx.clearRect(0, 0, width, height);

    // 数据处理
    const prices = priceData.map(d => d.price);
    const volumes = priceData.map(d => d.volume);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const maxVolume = Math.max(...volumes);
    
    const priceRange = maxPrice - minPrice;
    const pricePadding = priceRange * 0.1;

    // 价格Y轴比例
    const priceScale = (price: number) => {
      return padding.top + chartHeight - ((price - minPrice + pricePadding) / (priceRange + 2 * pricePadding)) * chartHeight;
    };

    // X轴比例
    const xScale = (index: number) => {
      return padding.left + (index / (priceData.length - 1)) * chartWidth;
    };

    // 成交量Y轴比例（底部区域）
    const volumeScale = (volume: number) => {
      const volumeHeight = chartHeight * 0.2;
      return height - padding.bottom - (volume / maxVolume) * volumeHeight;
    };

    // 绘制横盘期间背景
    volatilityPeriods.forEach(period => {
      if (period.is_sideways) {
        const startIndex = priceData.findIndex(d => d.date >= period.start_date);
        const endIndex = priceData.findIndex(d => d.date >= period.end_date);
        
        if (startIndex !== -1 && endIndex !== -1) {
          ctx.fillStyle = 'rgba(255, 193, 7, 0.1)';
          ctx.fillRect(
            xScale(startIndex),
            padding.top,
            xScale(endIndex) - xScale(startIndex),
            chartHeight
          );
          
          // 标注横盘天数
          ctx.fillStyle = '#f59e0b';
          ctx.font = '12px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(
            `横盘${period.days}天`,
            (xScale(startIndex) + xScale(endIndex)) / 2,
            padding.top + 20
          );
        }
      }
    });

    // 绘制价格线
    ctx.beginPath();
    ctx.strokeStyle = '#2563eb';
    ctx.lineWidth = 2;
    
    priceData.forEach((data, index) => {
      const x = xScale(index);
      const y = priceScale(data.price);
      
      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();

    // 绘制价格点
    priceData.forEach((data, index) => {
      const x = xScale(index);
      const y = priceScale(data.price);
      
      ctx.beginPath();
      ctx.fillStyle = '#2563eb';
      ctx.arc(x, y, 3, 0, 2 * Math.PI);
      ctx.fill();
    });

    // 绘制突破点
    breakoutPoints.forEach(breakout => {
      const dataIndex = priceData.findIndex(d => d.date === breakout.date);
      if (dataIndex !== -1) {
        const x = xScale(dataIndex);
        const y = priceScale(breakout.price);
        
        // 突破点标记
        ctx.beginPath();
        ctx.fillStyle = breakout.direction === 'upward' ? '#16a34a' : '#dc2626';
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.fill();
        
        // 突破箭头
        const arrowSize = 15;
        const arrowY = breakout.direction === 'upward' ? y - arrowSize : y + arrowSize;
        
        ctx.beginPath();
        ctx.fillStyle = breakout.direction === 'upward' ? '#16a34a' : '#dc2626';
        ctx.moveTo(x, arrowY);
        ctx.lineTo(x - arrowSize/2, arrowY + (breakout.direction === 'upward' ? arrowSize/2 : -arrowSize/2));
        ctx.lineTo(x + arrowSize/2, arrowY + (breakout.direction === 'upward' ? arrowSize/2 : -arrowSize/2));
        ctx.closePath();
        ctx.fill();
        
        // 突破标签
        ctx.fillStyle = breakout.direction === 'upward' ? '#16a34a' : '#dc2626';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(
          breakout.direction === 'upward' ? '向上突破' : '向下突破',
          x,
          arrowY + (breakout.direction === 'upward' ? -20 : 30)
        );
      }
    });

    // 绘制成交量柱状图
    priceData.forEach((data, index) => {
      const x = xScale(index);
      const volumeHeight = (height - padding.bottom) - volumeScale(data.volume);
      
      ctx.fillStyle = 'rgba(156, 163, 175, 0.6)';
      ctx.fillRect(x - 2, volumeScale(data.volume), 4, volumeHeight);
    });

    // 绘制坐标轴
    ctx.strokeStyle = '#d1d5db';
    ctx.lineWidth = 1;
    
    // Y轴
    ctx.beginPath();
    ctx.moveTo(padding.left, padding.top);
    ctx.lineTo(padding.left, height - padding.bottom);
    ctx.stroke();
    
    // X轴
    ctx.beginPath();
    ctx.moveTo(padding.left, height - padding.bottom);
    ctx.lineTo(width - padding.right, height - padding.bottom);
    ctx.stroke();

    // 绘制价格刻度
    const priceSteps = 5;
    for (let i = 0; i <= priceSteps; i++) {
      const price = minPrice + (priceRange / priceSteps) * i;
      const y = priceScale(price);
      
      ctx.fillStyle = '#6b7280';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'right';
      ctx.fillText(price.toFixed(2), padding.left - 10, y + 3);
      
      // 网格线
      ctx.strokeStyle = '#f3f4f6';
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();
    }

    // 绘制日期刻度
    const dateSteps = Math.min(5, priceData.length - 1);
    for (let i = 0; i <= dateSteps; i++) {
      const index = Math.floor((priceData.length - 1) * (i / dateSteps));
      const x = xScale(index);
      const date = new Date(priceData[index].date);
      
      ctx.fillStyle = '#6b7280';
      ctx.font = '12px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(
        `${date.getMonth() + 1}/${date.getDate()}`,
        x,
        height - padding.bottom + 20
      );
    }

    // 绘制标题和标签
    ctx.fillStyle = '#1f2937';
    ctx.font = 'bold 16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${stockName} (${stockCode}) - 波动性分析`, width / 2, 25);

    // Y轴标签
    ctx.save();
    ctx.translate(20, height / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillStyle = '#6b7280';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('价格', 0, 0);
    ctx.restore();

    // X轴标签
    ctx.fillStyle = '#6b7280';
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('日期', width / 2, height - 10);
  };

  const getPatternQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent': return 'text-green-600 bg-green-100';
      case 'good': return 'text-blue-600 bg-blue-100';
      case 'fair': return 'text-yellow-600 bg-yellow-100';
      case 'poor': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className={`bg-white rounded-lg shadow-sm border ${className}`}>
      {/* 图表头部信息 */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-600" />
            波动性分析图表
          </h3>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-200 rounded"></div>
              <span className="text-gray-600">横盘期</span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-green-600" />
              <span className="text-gray-600">向上突破</span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-red-600" />
              <span className="text-gray-600">向下突破</span>
            </div>
          </div>
        </div>

        {/* 分析指标 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-gray-600 mb-1">横盘天数</div>
            <div className="font-semibold text-gray-900">
              {currentAnalysis.sideways_period_days} 天
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-gray-600 mb-1">是否突破</div>
            <div className={`font-semibold ${currentAnalysis.has_breakout ? 'text-green-600' : 'text-gray-600'}`}>
              {currentAnalysis.has_breakout ? '是' : '否'}
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-gray-600 mb-1">突破方向</div>
            <div className={`font-semibold flex items-center gap-1 ${
              currentAnalysis.breakout_direction === 'upward' ? 'text-green-600' : 
              currentAnalysis.breakout_direction === 'downward' ? 'text-red-600' : 'text-gray-600'
            }`}>
              {currentAnalysis.breakout_direction === 'upward' && <TrendingUp className="w-4 h-4" />}
              {currentAnalysis.breakout_direction === 'downward' && <TrendingDown className="w-4 h-4" />}
              {currentAnalysis.breakout_direction === 'upward' ? '向上' : 
               currentAnalysis.breakout_direction === 'downward' ? '向下' : '无'}
            </div>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="text-gray-600 mb-1">波动性评分</div>
            <div className="font-semibold text-blue-600">
              {currentAnalysis.volatility_score.toFixed(1)}/10
            </div>
          </div>
        </div>

        {/* 模式质量 */}
        <div className="mt-3 flex items-center gap-2">
          <Info className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-600">模式质量：</span>
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getPatternQualityColor(currentAnalysis.pattern_quality)}`}>
            {currentAnalysis.pattern_quality === 'excellent' ? '优秀' :
             currentAnalysis.pattern_quality === 'good' ? '良好' :
             currentAnalysis.pattern_quality === 'fair' ? '一般' :
             currentAnalysis.pattern_quality === 'poor' ? '较差' : '未知'}
          </span>
        </div>
      </div>

      {/* 图表区域 */}
      <div ref={chartContainerRef} className="p-4">
        <canvas ref={canvasRef} className="w-full border rounded-lg bg-white" />
      </div>

      {/* 图表说明 */}
      <div className="px-4 pb-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Info className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-blue-800">
              <div className="font-medium mb-1">图表说明：</div>
              <ul className="space-y-1 text-xs">
                <li>• 黄色背景区域表示识别到的横盘整理期间</li>
                <li>• 蓝色线条表示股价走势，底部灰色柱状图表示成交量</li>
                <li>• 绿色/红色圆点和箭头标记向上/向下突破点</li>
                <li>• 横盘期是指股价波动幅度在20%以内且持续15天以上的时期</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VolatilityChart;