import React, { useState, useEffect, useRef } from 'react';
import { searchStocks } from '../services/api';

export interface StockInfo {
  symbol: string;
  name: string;
  short_name: string;
  market: string;
  industry: string;
}

interface StockSearchProps {
  onSelect: (stock: StockInfo) => void;
  placeholder?: string;
  autoFocus?: boolean;
  className?: string;
}

export const StockSearch: React.FC<StockSearchProps> = ({
  onSelect,
  placeholder = "搜索股票代码或名称...",
  autoFocus = false,
  className = ""
}) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<StockInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  
  // 防抖搜索
  useEffect(() => {
    const searchTimer = setTimeout(async () => {
      if (query.trim().length >= 1) {
        setIsLoading(true);
        try {
          const results = await searchStocks(query.trim(), 8);
          setSuggestions(results);
          setShowSuggestions(true);
          setSelectedIndex(-1);
        } catch (error) {
          console.error('搜索失败:', error);
          setSuggestions([]);
        } finally {
          setIsLoading(false);
        }
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
      }
    }, 300);

    return () => clearTimeout(searchTimer);
  }, [query]);

  // 键盘导航
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          handleSelect(suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  };

  const handleSelect = (stock: StockInfo) => {
    onSelect(stock);
    setQuery('');
    setSuggestions([]);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    inputRef.current?.blur();
  };

  const handleInputBlur = () => {
    // 延迟隐藏建议，以便点击建议项能够正常工作
    setTimeout(() => {
      setShowSuggestions(false);
      setSelectedIndex(-1);
    }, 200);
  };

  const highlightQuery = (text: string, query: string) => {
    if (!query) return text;
    
    const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => 
      regex.test(part) ? 
        <span key={index} className="stock-search-highlight">{part}</span> : 
        part
    );
  };

  return (
    <div className={`stock-search-container ${className}`}>
      <div className="stock-search-input-wrapper">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
          onBlur={handleInputBlur}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="stock-search-input"
        />
        
        {isLoading && (
          <div className="stock-search-loading">
            <div className="loading-spinner"></div>
          </div>
        )}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div ref={suggestionsRef} className="stock-search-suggestions">
          {suggestions.map((stock, index) => (
            <div
              key={`${stock.symbol}-${stock.market}`}
              className={`stock-search-suggestion-item ${
                index === selectedIndex ? 'selected' : ''
              }`}
              onClick={() => handleSelect(stock)}
              onMouseEnter={() => setSelectedIndex(index)}
            >
              <div className="stock-info">
                <div className="stock-primary">
                  <span className="stock-symbol">
                    {highlightQuery(stock.symbol, query)}
                  </span>
                  <span className="stock-name">
                    {highlightQuery(stock.name, query)}
                  </span>
                </div>
                <div className="stock-secondary">
                  <span className="stock-market">{stock.market}</span>
                  {stock.industry && (
                    <span className="stock-industry">{stock.industry}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showSuggestions && suggestions.length === 0 && query.trim() && !isLoading && (
        <div className="stock-search-suggestions">
          <div className="stock-search-no-results">
            <span>未找到相关股票</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default StockSearch;