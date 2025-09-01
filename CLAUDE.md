# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏗️ Architecture Overview

This is a **complete dual-version stock analysis chatbot** project with both CLI and modern web interfaces:

### Core Components
- **`stock_bot.py`**: CLI chatbot using asyncio, MCP protocol, and Qwen-Coder LLM
- **`backend/main.py`**: ✅ Complete FastAPI web server with embedded frontend
- **`backend/database.py`**: SQLite-based stock pool management with dataclass models  
- **`backend/stock_pool.db`**: SQLite database for holding/potential stock pools

### Data Flow Architecture

#### Web Version (Production Ready)
```
Web UI → WebSocket → FastAPI → WebStockAnalysisBot → MCP Client → AkShare Tools → AI Analysis
                         ↓
                    DatabaseManager → SQLite (stock_pool table)
```

#### CLI Version (Development/Testing)
```
Terminal → StockAnalysisBot → MCP Client → AkShare Tools → AI Analysis → Terminal Output
```

### Key Design Patterns
- **Async/Await**: All MCP communication and LLM calls are async
- **Tool Selection**: LLM chooses appropriate AkShare tools based on user query
- **Error Handling**: Detailed error classification for user-friendly messages (stock_bot.py:154-178)
- **Stock Name Mapping**: Hardcoded Chinese name → stock code conversion (stock_bot.py:28-41)

## 🚀 Development Commands

### Setup and Installation
```bash
# One-click installation (recommended)
./scripts/install.sh

# Manual installation
pip3 install -r requirements.txt          # CLI dependencies
pip3 install -r backend/requirements.txt  # Web dependencies
```

### Running the Application

#### Web Version (Production - Recommended)
```bash
# Using start script
./scripts/start.sh

# Direct startup  
python3 backend/main.py

# Access: http://localhost:8001
```

#### CLI Version (Development/Testing)
```bash
# Command line interface
python3 stock_bot.py
```

### Testing
```bash
# Browser automation testing (requires running web server)
node test_browser.js
```

## ✅ Current Status

### Completed Features
1. **✅ Complete Web Server**: `backend/main.py` fully implemented with FastAPI + embedded frontend
2. **✅ Fixed Start Script**: `scripts/start.sh` correctly launches the web application
3. **✅ WebSocket Real-time**: Full duplex communication with connection management
4. **✅ Stock Pool Management**: SQLite database with REST API endpoints
5. **✅ Responsive Web UI**: Modern chat interface with mobile support

### Environment Configuration
- **Configuration Template**: `.env.template` with comprehensive setup guide
- **Configuration Management**: `config/settings.py` with Pydantic validation
- **Required Variables**: `API_KEY`, `AKSHARE_MCP_PATH`  
- **Optional Variables**: `SERVER_HOST`, `SERVER_PORT`, `DEBUG`, `LOG_LEVEL`
- **Configuration Validation**: Run `python3 config/settings.py` to validate setup

## 🔧 Development Guidelines

### When Adding Features
- **Web Features**: Extend `WebStockAnalysisBot` class in `backend/main.py`
- **CLI Features**: Extend `StockAnalysisBot` class in `stock_bot.py`
- **Database Features**: Add methods to `DatabaseManager` class in `database.py`
- **Stock Mappings**: Update `stock_name_map` dictionary in both versions
- **API Endpoints**: Add new FastAPI routes in `backend/main.py`
- **Frontend**: Modify embedded HTML in the `get()` function

### Testing Approach
- **Manual Testing**: Interactive testing via web interface and CLI
- **Automated Testing**: `test_browser.js` for web UI automation
- **API Testing**: Use `/health` endpoint to verify service status
- **MCP Testing**: Test connection independently before running bot
- **Integration Testing**: Verify both CLI and Web versions work with same backend

### Architecture Highlights
- **Async Framework**: Full async/await pattern with FastAPI and AsyncIO
- **WebSocket Management**: Connection pooling with automatic reconnection
- **Embedded Frontend**: Single-file deployment with built-in HTML/CSS/JS
- **Dual Interface**: Both CLI and Web versions share core business logic
- **Database Integration**: SQLite with transaction support and error handling

## 🎯 Development Roadmap

### ✅ Phase 1: Core Web Architecture (Completed)
1. ✅ Created `backend/main.py` FastAPI server with WebSocket support
2. ✅ Implemented embedded HTML frontend with modern UI
3. ✅ Fixed start script and deployment process
4. ✅ Resolved environment configuration conflicts

### 🚧 Phase 2: Feature Enhancement (Optional)
1. Add real-time stock price updates in web interface
2. Implement user authentication and session management
3. Add stock portfolio performance analytics
4. Create mobile app companion
5. Add more technical indicators and chart visualization

### 🔮 Phase 3: Advanced Features (Future)
1. Multi-language support (English, Chinese)
2. Integration with more data sources
3. Advanced AI models for market prediction
4. Social trading features and stock discussion

## 📋 Quick Reference

### Key Files and Their Roles
- **`backend/main.py`** - FastAPI web application with frontend file serving
- **`frontend/`** - Separated frontend files (HTML/CSS/JS)
- **`stock_bot.py`** - CLI version with identical AI functionality  
- **`backend/database.py`** - Database layer with comprehensive stock pool management
- **`config/settings.py`** - Configuration management with Pydantic validation
- **`.env.template`** - Comprehensive configuration template

### Important Code Locations
- **WebSocket Handler**: `backend/main.py:332-354`
- **AI Query Processing**: `backend/main.py:90-208` (Web) / `stock_bot.py:82-208` (CLI)
- **Stock Name Mapping**: `backend/main.py:32-41` / `stock_bot.py:28-41`
- **Database Models**: `backend/database.py:8-18`
- **API Endpoints**: `backend/main.py:356-368`

### Code Quality Features
- ✅ Full async/await implementation
- ✅ Comprehensive error handling and user-friendly messages
- ✅ Type hints with Pydantic models
- ✅ Transaction-safe database operations
- ✅ WebSocket connection management with auto-reconnect
- ✅ Responsive design with mobile support

### Current Production Status
**🟢 READY FOR PRODUCTION**
- Web application fully functional at http://localhost:8001
- CLI version available for development/testing
- Database properly initialized and integrated
- All dependencies resolved and tested