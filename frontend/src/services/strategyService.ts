// 策略服务 - 处理高级筛选和策略配置
interface StrategyConfig {
  strategy_id: string;
  enabled: boolean;
  parameters: Record<string, any>;
  weight: number;
}

interface AdvancedScreeningRequest {
  strategies: StrategyConfig[];
  market_filter: string[];
  min_market_cap?: number;
  max_market_cap?: number;
  limit: number;
}

// interface StrategyGroup {
//   id: string;
//   strategies: string[];
// }

interface AvailableStrategies {
  groups: Record<string, string[]>;
  total_count: number;
}

interface ScreeningResult {
  results: any[];
  summary: {
    total_found: number;
    after_strategy_filter: number;
    strategies_used: number;
    filter_efficiency: number;
  };
}

interface TestResult {
  test_results: Array<{
    strategy_id: string;
    status: string;
    test_score: number;
    parameters: Record<string, any>;
  }>;
  summary: {
    total_strategies: number;
    enabled_strategies: number;
    passed_tests: number;
  };
}

class StrategyService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001';
  }

  /**
   * 获取所有可用的策略
   */
  async getAvailableStrategies(): Promise<AvailableStrategies> {
    try {
      const response = await fetch(`${this.baseUrl}/api/strategies/available`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const result = await response.json();
      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.message || '获取策略列表失败');
      }
    } catch (error) {
      console.error('获取可用策略失败:', error);
      throw error;
    }
  }

  /**
   * 测试策略配置
   */
  async testStrategies(request: AdvancedScreeningRequest): Promise<TestResult> {
    try {
      const response = await fetch(`${this.baseUrl}/api/strategies/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.message || '策略测试失败');
      }
    } catch (error) {
      console.error('策略测试失败:', error);
      throw error;
    }
  }

  /**
   * 执行高级策略筛选
   */
  async performAdvancedScreening(request: AdvancedScreeningRequest): Promise<ScreeningResult> {
    try {
      const response = await fetch(`${this.baseUrl}/api/advanced-screening`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      if (result.success) {
        return result.data;
      } else {
        throw new Error(result.message || '筛选失败');
      }
    } catch (error) {
      console.error('高级筛选失败:', error);
      throw error;
    }
  }

  /**
   * 构建策略配置请求
   */
  buildScreeningRequest(
    selectedStrategies: Set<string>,
    strategyParameters: Record<string, Record<string, any>>,
    strategyWeights: Record<string, number>,
    options: {
      marketFilter?: string[];
      minMarketCap?: number;
      maxMarketCap?: number;
      limit?: number;
    } = {}
  ): AdvancedScreeningRequest {
    const strategies: StrategyConfig[] = Array.from(selectedStrategies).map(strategyId => ({
      strategy_id: strategyId,
      enabled: true,
      parameters: strategyParameters[strategyId] || {},
      weight: strategyWeights[strategyId] || 1.0
    }));

    return {
      strategies,
      market_filter: options.marketFilter || ['SH', 'SZ'],
      min_market_cap: options.minMarketCap,
      max_market_cap: options.maxMarketCap,
      limit: options.limit || 50
    };
  }

  /**
   * 保存策略模板
   */
  async saveStrategyTemplate(template: {
    name: string;
    description: string;
    strategies: StrategyConfig[];
  }): Promise<void> {
    try {
      // 暂时使用localStorage保存模板
      const templates = this.getStrategyTemplates();
      const newTemplate = {
        id: Date.now().toString(),
        ...template,
        created_at: new Date().toISOString()
      };
      templates.push(newTemplate);
      localStorage.setItem('strategy_templates', JSON.stringify(templates));
    } catch (error) {
      console.error('保存策略模板失败:', error);
      throw error;
    }
  }

  /**
   * 获取策略模板
   */
  getStrategyTemplates(): any[] {
    try {
      const templates = localStorage.getItem('strategy_templates');
      return templates ? JSON.parse(templates) : [];
    } catch (error) {
      console.error('获取策略模板失败:', error);
      return [];
    }
  }

  /**
   * 删除策略模板
   */
  async deleteStrategyTemplate(templateId: string): Promise<void> {
    try {
      const templates = this.getStrategyTemplates();
      const filteredTemplates = templates.filter(t => t.id !== templateId);
      localStorage.setItem('strategy_templates', JSON.stringify(filteredTemplates));
    } catch (error) {
      console.error('删除策略模板失败:', error);
      throw error;
    }
  }

  /**
   * 导出策略配置
   */
  exportStrategyConfig(config: AdvancedScreeningRequest): string {
    return JSON.stringify(config, null, 2);
  }

  /**
   * 导入策略配置
   */
  importStrategyConfig(configString: string): AdvancedScreeningRequest {
    try {
      return JSON.parse(configString);
    } catch (error) {
      throw new Error('无效的配置格式');
    }
  }

  /**
   * 验证策略配置
   */
  validateStrategyConfig(config: AdvancedScreeningRequest): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!config.strategies || config.strategies.length === 0) {
      errors.push('至少需要选择一个策略');
    }

    const enabledStrategies = config.strategies.filter(s => s.enabled);
    if (enabledStrategies.length === 0) {
      errors.push('至少需要启用一个策略');
    }

    if (!config.market_filter || config.market_filter.length === 0) {
      errors.push('至少需要选择一个市场');
    }

    if (config.limit && (config.limit < 1 || config.limit > 1000)) {
      errors.push('筛选数量应在1-1000之间');
    }

    // 验证策略参数
    enabledStrategies.forEach(strategy => {
      if (!strategy.strategy_id) {
        errors.push(`策略ID不能为空`);
      }
      if (strategy.weight <= 0) {
        errors.push(`策略${strategy.strategy_id}的权重必须大于0`);
      }
    });

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * 格式化筛选结果
   */
  formatScreeningResults(results: any[]): any[] {
    return results.map(result => ({
      ...result,
      // 计算综合评级
      grade: this.calculateGrade(result.weighted_score),
      // 格式化策略得分
      strategy_summary: this.formatStrategyScores(result.strategy_scores || []),
      // 添加推荐理由
      recommendation: this.generateRecommendation(result)
    }));
  }

  private calculateGrade(score: number): string {
    if (score >= 90) return 'A+';
    if (score >= 85) return 'A';
    if (score >= 80) return 'A-';
    if (score >= 75) return 'B+';
    if (score >= 70) return 'B';
    if (score >= 65) return 'B-';
    if (score >= 60) return 'C+';
    if (score >= 55) return 'C';
    return 'C-';
  }

  private formatStrategyScores(scores: any[]): string {
    if (scores.length === 0) return '无策略评分';
    
    const topScores = scores
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(s => `${s.strategy_id.replace(/_/g, ' ')}(${s.score}分)`)
      .join(', ');
    
    return `主要信号: ${topScores}`;
  }

  private generateRecommendation(result: any): string {
    const score = result.weighted_score;
    
    if (score >= 85) {
      return '强烈推荐 - 多项策略信号强烈一致';
    } else if (score >= 75) {
      return '推荐 - 策略信号积极正面';
    } else if (score >= 65) {
      return '关注 - 策略信号偏积极';
    } else {
      return '观望 - 策略信号一般';
    }
  }
}

// 创建单例实例
export const strategyService = new StrategyService();
export default strategyService;