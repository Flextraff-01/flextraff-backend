# FlexTraff Backend - Adaptive Traffic Control System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.13.5-blue.svg)](https://python.org)
[![Supabase](https://img.shields.io/badge/Database-Supabase-green.svg)](https://supabase.com)
[![Tests](https://img.shields.io/badge/Tests-64%20passing-brightgreen.svg)](#testing)
[![Deployment](https://img.shields.io/badge/Deploy-Live%20on%20Render-brightgreen.svg)](https://flextraff-backend-production.up.railway.app/)

## 🌐 Live Demo

**Production API:** [https://flextraff-backend-production.up.railway.app/](https://flextraff-backend-production.up.railway.app/)
- **Health Check:** [/health](https://flextraff-backend-production.up.railway.app/health)
- **Interactive Docs:** [/docs](https://flextraff-backend-production.up.railway.app/docs)
- **OpenAPI Schema:** [/openapi.json](https://flextraff-backend-production.up.railway.app/openapi.json)

## 🚦 Overview

FlexTraff Backend is an intelligent **Adaptive Traffic Control System (ATCS)** that optimizes traffic light timing based on real-time vehicle detection data. Built with FastAPI and Supabase, it provides REST APIs for traffic management, historical analysis, and real-time monitoring.

### Key Features

- 🧮 **Intelligent Traffic Algorithms**: ATCS-based timing calculations
- 🔄 **Real-time Processing**: Live vehicle detection and timing updates  
- 📊 **Historical Analytics**: Traffic pattern analysis and reporting
- 🚀 **High Performance**: <100ms response times for calculations
- 🧪 **Comprehensive Testing**: 64 tests across 7 categories
- 📱 **RESTful APIs**: Easy integration with frontend applications
- 🔒 **Secure**: JWT authentication and data validation using supabase

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd flextraff-backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file in the project root:

```env
# Database Configuration (Supabase)
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# API Configuration
API_HOST=127.0.0.1
API_PORT=8001
```

### 3. Run the Application

```bash
# Start the FastAPI server
python main.py

# The API will be available at:
# - Base URL: http://127.0.0.1:8001
# - Documentation: http://127.0.0.1:8001/docs
```

### 4. Test the System

```bash
# Run comprehensive test suite
python run_tests.py comprehensive

# Or run specific test categories
python run_tests.py unit          # Fast unit tests
python run_tests.py algorithm     # Algorithm validation
python run_tests.py integration   # Full integration tests
```

## 📚 Documentation

| Document | Description |
|----------|-------------|

| **[🔌 API Reference](docs/API_GUIDE.md)** | Detailed API endpoint documentation |
| **[🧪 Testing Guide](docs/TESTING_GUIDE.md)** | Comprehensive testing documentation |

## 🏗️ Architecture

### Core Components

1. **🧮 Traffic Calculator Service** (`app/services/traffic_calculator.py`)
   - ATCS algorithm implementation
   - Intelligent timing calculations with constraint validation
   - Edge case handling for various traffic scenarios

2. **🗄️ Database Service** (`app/services/database_service.py`)
   - Supabase PostgreSQL integration
   - Real-time vehicle detection logging
   - Historical data management and analytics

3. **🚀 FastAPI Application** (`main.py`)
   - RESTful API endpoints
   - Real-time traffic calculations
   - CORS support and comprehensive error handling

### Data Flow

```
Vehicle Detection → Database → Algorithm → Optimal Timing → API Response
```

## 🔌 API Endpoints

### Core Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System health check with database status |
| `/junctions` | GET | List all traffic junctions |
| `/calculate-timing` | POST | **Calculate optimal traffic timing** |
| `/vehicle-detection` | POST | Record vehicle detection events |
| `/junction/{id}/status` | GET | Real-time junction status |
| `/junction/{id}/history` | GET | Historical traffic data |
| `/live-timing` | GET | Live timing for all junctions |

### Example Usage

```bash
# Calculate optimal timing for a junction
curl -X POST http://127.0.0.1:8001/calculate-timing \
  -H "Content-Type: application/json" \
  -d '{
    "lane_counts": [25, 30, 20, 15],
    "junction_id": 1
  }'

# Response
{
  "green_times": [38, 45, 32, 25],
  "cycle_time": 140,
  "efficiency_score": 0.87
}
```

## 🧪 Testing

The project includes a comprehensive test suite with **64 tests** across 7 categories:

### Test Categories

| Category | Tests | Purpose | Runtime |
|----------|-------|---------|---------|
| **Unit** | 44 | Fast tests with mocked dependencies | ~1s |
| **Algorithm** | 13 | Traffic calculation validation | ~1s |
| **Integration** | 24 | Tests with real database/API | ~3-5s |
| **Performance** | 4 | Load testing and benchmarks | ~30s |
| **Database** | 10 | Database operations testing | ~2-8s |
| **API** | 49 | Endpoint functionality testing | Varies |
| **Slow** | 4 | Long-running test scenarios | ~5-10s |

### Running Tests

```bash
# Quick test suite (recommended for development)
python run_tests.py quick

# Comprehensive test suite (all categories)
python run_tests.py comprehensive

# Specific test categories
python run_tests.py unit          # Fast unit tests
python run_tests.py algorithm     # Algorithm validation  
python run_tests.py integration   # Integration tests (requires API server)
python run_tests.py performance   # Performance benchmarks

# Traditional pytest commands
pytest tests/test_traffic_algorithm.py -v
pytest -m "unit and api" -v
```

### Test Output Example

```
📊 TEST METRICS BY CATEGORY
        unit:  44 tests - Unit tests with mocked dependencies
 integration:  24 tests - Integration tests with real database
 performance:   4 tests - Performance and load tests
   algorithm:  13 tests - Algorithm-specific tests
         api:  49 tests - API endpoint tests
    database:  10 tests - Database-related tests
        slow:   4 tests - Slow-running tests

Total: 64 tests passed ✅
```

## 🎯 ATCS Algorithm Features

The FlexTraff system implements an advanced **Adaptive Traffic Control System (ATCS)** algorithm:

### Core Algorithm Features

- **🔄 Proportional Distribution**: Fair green time allocation based on traffic density
- **⚖️ Constraint Management**: Enforces minimum (15s) and maximum (75s) timing limits  
- **🎯 Edge Case Handling**: Optimizes for light traffic, zero traffic, and uneven distribution
- **⚡ Real-time Processing**: Dynamic timing adjustments with <100ms response times
- **🧮 Mathematical Precision**: Accurate calculations ensuring cycle time constraints

### Traffic Scenarios Handled

| Scenario | Example Input | Algorithm Response |
|----------|---------------|-------------------|
| **Balanced Traffic** | `[25, 30, 20, 15]` | Proportional timing: `[38, 45, 32, 25]` |
| **Heavy Traffic** | `[60, 80, 70, 50]` | Constrained timing: `[52, 69, 61, 43]` |
| **Light Traffic** | `[5, 8, 3, 2]` | Minimum timing: `[28, 44, 21, 15]` |
| **Zero Traffic** | `[0, 0, 0, 0]` | Equal distribution: `[15, 15, 15, 15]` |
| **Uneven Distribution** | `[80, 5, 10, 5]` | Optimized: `[75, 15, 20, 15]` |

## 📦 Dependencies

All dependencies are managed in `requirements.txt` for easy installation:

### Core Dependencies
- **FastAPI 0.115.0**: Modern web framework
- **Uvicorn 0.32.0**: ASGI server
- **Supabase 2.9.0**: Database integration
- **Pydantic 2.10.0**: Data validation

### Development Dependencies  
- **Pytest 8.3.3**: Testing framework
- **Pytest-asyncio 0.24.0**: Async testing support
- **AioHTTP 3.11.7**: HTTP client for integration tests

### Installation
```bash
pip install -r requirements.txt
```

All dependencies are pinned to specific versions for reproducible builds.

## 🚀 Production Deployment

### Environment Variables

```env
# Required for production
SUPABASE_URL=your_production_supabase_url
SUPABASE_ANON_KEY=your_production_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Optional configuration
API_HOST=0.0.0.0
API_PORT=8000
JWT_SECRET_KEY=your_secret_key
LOG_LEVEL=INFO
```

### Production Run Command

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 🔧 Development

### Code Quality & Linting

**🔍 Before pushing to any branch, ensure your code passes linting:**

```bash
# Quick linting check
./scripts/pre-push-lint.sh

# Or install pre-commit for automatic checks
pip install pre-commit
pre-commit install
```

**📋 Linting runs automatically on all branches via GitHub Actions**
- See [Linting Guidelines](docs/LINTING_GUIDELINES.md) for detailed setup

### Running the Application

1. **Start the API server:**
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

2. **Access the API:**
- API Documentation: http://127.0.0.1:8001/docs
- Health Check: http://127.0.0.1:8001/health
- Root Endpoint: http://127.0.0.1:8001/

## 📚 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | API information and status |
| `GET` | `/health` | Health check and database status |
| `POST` | `/calculate-timing` | Calculate traffic light timing |
| `POST` | `/vehicle-detection` | Log vehicle detection event |
| `GET` | `/junctions` | Get all active junctions |

### Junction-Specific Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/junction/{id}/status` | Current junction status |
| `GET` | `/junction/{id}/live-timing` | Real-time timing calculation |
| `GET` | `/junction/{id}/history` | Traffic history and cycles |

### Analytics Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/analytics/daily-summary` | Daily traffic summary |

## 🧪 Testing

### Run Algorithm Tests
```bash
python -m pytest tests/test_traffic_algorithm.py -v
```

### Run Database Integration Test
```bash
python test_database_integration.py
```

### Run API Tests
```bash
python simple_api_test.py
```

### Test Results Summary
- ✅ 13/13 Algorithm test cases passing
- ✅ Database integration working
- ✅ All API endpoints functional
- ✅ Real-time calculation verified

## 🔧 Configuration

### Environment Variables

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key

# API Configuration (optional)
API_HOST=127.0.0.1
API_PORT=8001
DEBUG=true
```

### Algorithm Parameters

```python
# Traffic Calculator Configuration
MIN_CYCLE_TIME = 60     # Minimum cycle time (seconds)
MAX_CYCLE_TIME = 180    # Maximum cycle time (seconds)
MIN_GREEN_TIME = 15     # Minimum green light duration
MAX_GREEN_TIME = 90     # Maximum green light duration
LIGHT_TRAFFIC_THRESHOLD = 15  # Threshold for light traffic mode
```

## 📊 Database Schema

### Key Tables

1. **traffic_junctions**
   - Junction management and configuration
   - Location and timing parameters

2. **vehicle_detections**
   - Real-time vehicle detection logs
   - FASTag and vehicle type tracking

3. **traffic_cycles**
   - Traffic timing calculation results
   - Algorithm execution history

## 🎯 Use Cases

### Real-time Traffic Management
```python
# Example: Calculate timing for current traffic
lane_counts = [45, 38, 52, 41]  # Vehicles per lane
green_times, cycle_time = await calculator.calculate_green_times(
    lane_counts, junction_id=3
)
```

### Vehicle Detection Logging
```python
# Example: Log vehicle detection
await db_service.log_vehicle_detection(
    junction_id=3,
    lane_number=1,
    fastag_id="FT123456789",
    vehicle_type="car"
)
```

### Live Timing API Call
```bash
curl -X POST "http://127.0.0.1:8001/calculate-timing" \
     -H "Content-Type: application/json" \
     -d '{"lane_counts": [45, 38, 52, 41], "junction_id": 3}'
```

## 🔮 Future Enhancements

- [ ]Computer Vision for vehicle type like bike,autorickshaw
- [ ] Machine Learning integration for prediction
- [ ] Weather condition adjustments
- [ ] Emergency vehicle priority
- [ ] Historical analytics and reporting
- [ ] Multi-junction coordination
- [ ] Mobile app integration









<!-- ------------------------------- BAD MD GENERATED BY AI AGENT -------------------------------------- -->


<!-- ## 🛠️ Development

### Project Structure
```
flextraff-backend/
## 🏗️ Project Structure

```
flextraff-backend/
├── app/                          # Application core
│   ├── services/                 # Business logic services
│   │   ├── traffic_calculator.py    # Traffic timing algorithms
│   │   ├── database_service.py      # Database operations
│   │   └── custom_auth_service.py   # Authentication service
│   └── middleware/               # Custom middleware
│       └── auth_middleware.py        # JWT authentication
├── tests/                        # Test suite
│   ├── test_traffic_algorithm.py    # Algorithm tests
│   ├── test_api_endpoints.py        # Unit tests
│   ├── test_api_integration.py      # Integration tests
│   ├── test_performance.py          # Performance tests
│   └── conftest.py                  # Test configuration
├── docs/                         # Documentation
├── main.py                       # FastAPI application entry point
├── run_tests.py                  # Enhanced test runner
├── requirements.txt              # Python dependencies
├── pytest.ini                   # Test configuration
└── .env                         # Environment variables (create this)
```


### Adding New Features

1. **New Algorithm Logic**: Extend `TrafficCalculator` class
2. **Database Operations**: Add methods to `DatabaseService`
3. **API Endpoints**: Add routes to `main.py`
4. **Tests**: Add test cases to `tests/` directory

## 📞 Support

For questions, issues, or contributions:
- Check the API documentation at `/docs`
- Run health checks at `/health`
- Review test results for validation

## 🏆 Status

**Current Version**: 1.0.0
**Status**: ✅ Production Ready
**Last Updated**: September 2025

### Component Status
- ✅ Core Algorithm: Fully implemented and tested
- ✅ Database Integration: Complete with Supabase
- ✅ API Endpoints: All endpoints functional
- ✅ Testing Suite: Comprehensive test coverage
- ✅ Documentation: Complete API documentation
- 🚧 Frontend Integration: Ready for React frontend
- 🚧 Authentication: Deferred to future iteration

## 🔗 Integration Notes

This project is designed to integrate with the FlexTraff Admin Panel at:
https://github.com/MananBagga/Flextraff-Admin-Panel

- API documentation will be available at `/docs` when the server is running
- Additional documentation can be found in the `docs/` directory

# CI/CD Pipeline Test - Mon Sep 15 14:50:05 IST 2025
# CI/CD Pipeline Test - Mon Sep 15 14:50:59 IST 2025 -->
