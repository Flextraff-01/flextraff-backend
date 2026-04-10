# FlexTraff Testing Guide

## 🧪 Testing Overview

FlexTraff backend includes a comprehensive test suite designed to ensure reliability, performance, and correctness of the adaptive traffic control system. This guide covers all testing aspects, from setup to execution and interpretation of results.

## 🏗️ Test Architecture

### Test Categories

The test suite is organized into 7 distinct categories, each serving a specific purpose:

| Category | Purpose | Dependencies | Test Count |
|----------|---------|--------------|------------|
| **Unit** | Fast tests with mocked dependencies | None | 44 tests |
| **Integration** | Tests with real database connections | API server + Database | 24 tests |
| **Performance** | Load testing and timing benchmarks | API server | 4 tests |
| **Algorithm** | Traffic calculation algorithm validation | None | 13 tests |
| **API** | Endpoint functionality testing | Varies | 49 tests |
| **Database** | Database operations testing | Database | 10 tests |
| **Slow** | Long-running test scenarios | API server | 4 tests |

### Test Infrastructure

```
tests/
├── conftest.py                   # Test configuration and fixtures
├── test_traffic_algorithm.py     # Algorithm validation tests
├── test_api_endpoints.py         # Unit tests for API endpoints
├── test_api_integration.py       # Integration tests with live API
├── test_performance.py           # Performance and load tests
└── pytest.ini                   # Pytest configuration
```

## 🚀 Running Tests

### Enhanced Test Runner


The project includes a sophisticated test runner (`run_tests.py`) that provides multiple execution modes:

```bash
# Basic test execution
python run_tests.py <category>

# Available categories
python run_tests.py unit          # Unit tests only
python run_tests.py integration   # Integration tests
python run_tests.py performance   # Performance tests
python run_tests.py algorithm     # Algorithm tests
python run_tests.py database      # Database tests
python run_tests.py slow          # Slow-running tests
python run_tests.py api           # API tests (by marker)
```

### Test Suites

```bash
# Pre-configured test suites
python run_tests.py quick         # Unit + Algorithm tests (fast)
python run_tests.py all           # All test files
python run_tests.py comprehensive # All categories with detailed metrics
python run_tests.py ci            # CI/CD optimized suite
```

### Direct Pytest Commands

```bash
# Run specific test files
pytest tests/test_traffic_algorithm.py -v
pytest tests/test_api_endpoints.py -v

# Run by markers
pytest -m unit -v                 # All unit tests
pytest -m "integration and api" -v # Integration tests for API
pytest -m "not slow" -v           # Exclude slow tests

# Run with coverage
pytest --cov=app tests/

# Run specific test methods
pytest tests/test_traffic_algorithm.py::TestTrafficCalculator::test_basic_calculation -v
```

## 🏷️ Test Markers & Categories

### Pytest Markers

Tests are marked with categories for flexible execution:

```python
@pytest.mark.unit          # Unit tests with mocked dependencies
@pytest.mark.integration   # Integration tests with real database
@pytest.mark.performance   # Performance and load tests
@pytest.mark.slow          # Slow-running tests
@pytest.mark.api           # API endpoint tests
@pytest.mark.algorithm     # Algorithm-specific tests
@pytest.mark.database      # Database-related tests
```

### Marker Combinations

Many tests have multiple markers for flexible filtering:

```python
@pytest.mark.unit
@pytest.mark.api
class TestAPIEndpoints:
    # This test is both a unit test AND an API test
```

## 📊 Test Execution Output

### Comprehensive Test Results

The enhanced test runner provides detailed execution metrics:

```
================================================================================
📊 TEST EXECUTION SUMMARY
================================================================================
Total Test Suites: 9
Passed: 6 ✅
Failed: 3 ❌
Success Rate: 66.7%

Individual Tests: 64
Passed: 64 ✅
Failed: 0 ❌
Total Duration: 58.47 seconds

Detailed Results:
------------------------------------------------------------
✅ PASS   Algorithm Tests                (1.03s)
         13 tests - 13 passed, 0 failed
✅ PASS   Unit Tests (API Endpoints)     (0.99s)
         31 tests - 31 passed, 0 failed
✅ PASS   Database Integration Test      (7.59s)
❌ FAIL   Performance Tests              (30.69s)
✅ PASS   Basic API Test                 (0.59s)

================================================================================
📊 TEST METRICS BY CATEGORY
================================================================================
        unit:  44 tests - Unit tests with mocked dependencies
 integration:  24 tests - Integration tests with real database
 performance:   4 tests - Performance and load tests
        slow:   4 tests - Slow-running tests
         api:  49 tests - API endpoint tests
   algorithm:  13 tests - Algorithm-specific tests
    database:  10 tests - Database-related tests
```

## 🧩 Test Categories Detailed

### 1. Unit Tests (44 tests)

**Purpose**: Fast, isolated tests with no external dependencies  
**Location**: `tests/test_api_endpoints.py`  
**Runtime**: ~1 second  
**Dependencies**: None (uses mocked services)

**What they test**:
- API endpoint logic
- Request/response validation  
- Pydantic model validation
- Error handling
- Business logic with mocked dependencies

**Example**:
```bash
python run_tests.py unit
```

**Sample Output**:
```
🧪 Running Unit Tests (API Endpoints)
Duration: 0.99 seconds
31 tests - 31 passed, 0 failed
```

### 2. Algorithm Tests (13 tests)

**Purpose**: Validate traffic calculation algorithms  
**Location**: `tests/test_traffic_algorithm.py`  
**Runtime**: ~1 second  
**Dependencies**: None (pure algorithm testing)

**What they test**:
- Traffic timing calculations
- Edge cases (zero traffic, maximum traffic)
- Algorithm correctness
- Mathematical precision
- Real-world scenarios

**Test scenarios**:
- Basic calculations with balanced traffic
- Heavy traffic scenarios
- Uneven traffic distribution
- Edge cases (zero/maximum counts)
- Cycle time constraints
- Real sample data validation

**Example**:
```bash
python run_tests.py algorithm
```

### 3. Integration Tests (24 tests)

**Purpose**: Test with real API server and database connections  
**Location**: `tests/test_api_integration.py`  
**Runtime**: ~3-5 seconds  
**Dependencies**: Running API server at http://127.0.0.1:8001

**Prerequisites**:
```bash
# Start the API server first
python main.py

# Then run integration tests
python run_tests.py integration
```

**What they test**:
- End-to-end API functionality
- Real database operations
- Network connectivity
- Authentication flows
- Data persistence
- Cross-service integration

### 4. Performance Tests (4 tests)

**Purpose**: Load testing and performance benchmarks  
**Location**: `tests/test_performance.py`  
**Runtime**: ~30 seconds  
**Dependencies**: Running API server

**What they test**:
- Single request response times
- Concurrent request handling
- Sustained load performance
- Response time distribution
- Throughput measurements
- System stability under load

**Performance Metrics**:
- Response time < 100ms for single calculations
- Concurrent load handling (50+ requests)
- Sustained throughput measurements
- Memory and CPU usage patterns

**Example**:
```bash
# Ensure API server is running
python main.py &

# Run performance tests
python run_tests.py performance
```

### 5. Database Tests (10 tests)

**Purpose**: Database operations and data integrity  
**Location**: `tests/test_api_integration.py` (marked with `@pytest.mark.database`)  
**Runtime**: ~2-8 seconds  
**Dependencies**: Supabase database connection

**What they test**:
- CRUD operations
- Data validation
- Transaction handling
- Constraint enforcement
- Query performance
- Data relationships

### 6. API Tests (49 tests)

**Purpose**: API endpoint functionality across categories  
**Location**: Multiple files with `@pytest.mark.api`  
**Runtime**: Varies  
**Dependencies**: Varies by test

**What they test**:
- HTTP methods and status codes
- Request/response formats
- Authentication and authorization
- Input validation
- Error responses
- API contract compliance

### 7. Slow Tests (4 tests)

**Purpose**: Long-running scenarios and stress tests  
**Location**: `tests/test_performance.py` (marked with `@pytest.mark.slow`)  
**Runtime**: ~5-10 seconds  
**Dependencies**: Running API server

**What they test**:
- Extended load scenarios
- Long-running calculations
- Memory leak detection
- System stability over time
- Resource cleanup

## 🔧 Test Configuration

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function

# Markers for test categorization
markers =
    unit: Unit tests with mocked dependencies
    integration: Integration tests with real database
    performance: Performance and load tests
    slow: Slow-running tests
    api: API endpoint tests
    algorithm: Algorithm-specific tests
    database: Database-related tests

# Output configuration
addopts = 
    -v
    --tb=short
    --strict-markers
    --color=yes
    --durations=10
```

### Test Fixtures (`tests/conftest.py`)

**Key fixtures**:
- `client`: FastAPI test client with mocked dependencies
- `aio_session`: Async HTTP session for integration tests
- `mock_db_service`: Mocked database service
- `mock_traffic_calculator`: Mocked traffic calculator
- `TestData`: Common test data and validation functions

## 🚦 Prerequisites & Setup

### Environment Setup

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Environment Variables** (for integration/database tests):
```bash
# Required for database tests
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
SUPABASE_SERVICE_ROLE_KEY=your_service_key
```

3. **Database Setup**: Ensure Supabase database is accessible with test data

### Running API Server for Integration Tests

```bash
# Start server in background
python main.py &

# Or start in separate terminal
python main.py

# Verify server is running
curl http://127.0.0.1:8001/health
```

### Test Database Requirements

For integration and database tests, ensure:
- Valid Supabase connection
- Test junctions exist in database
- Proper permissions for CRUD operations

## 📈 Understanding Test Results

### Success Indicators

✅ **All Pass**: Green output, exit code 0  
✅ **Partial Pass**: Some categories pass, others have expected failures  
✅ **Performance within bounds**: Response times meet thresholds  

### Common "Failures" (Not actual issues)

❌ **Performance threshold failures**: Tests expecting <50ms response times might fail due to network latency  
❌ **Server not running**: Integration tests fail if API server isn't started  
❌ **Database connectivity**: Database tests fail without proper Supabase setup  

### Debugging Test Failures

1. **Check Dependencies**:
```bash
# Verify API server
curl http://127.0.0.1:8001/health

# Verify database connection
python -c "from app.services.database_service import DatabaseService; print('DB OK')"
```

2. **Run Individual Tests**:
```bash
# Run single test with maximum verbosity
pytest tests/test_traffic_algorithm.py::TestTrafficCalculator::test_basic_calculation -vvv
```

3. **Check Logs**:
```bash
# Run with logging output
pytest -s tests/test_api_integration.py
```

## 🎯 Best Practices

### Writing New Tests

1. **Use appropriate markers**:
```python
@pytest.mark.unit
@pytest.mark.api
def test_my_endpoint():
    pass
```

2. **Follow naming conventions**:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test methods: `test_*`

3. **Use fixtures for setup**:
```python
def test_with_client(client):
    response = client.get("/health")
    assert response.status_code == 200
```

4. **Test edge cases**:
```python
def test_invalid_input():
    # Test with invalid data
    response = client.post("/calculate-timing", json={"invalid": "data"})
    assert response.status_code == 422
```

### Running Tests in CI/CD

```bash
# CI-optimized test suite
python run_tests.py ci

# With coverage reporting
pytest --cov=app --cov-report=xml tests/
```

### Performance Testing Guidelines

1. **Baseline measurements**: Establish performance baselines
2. **Consistent environment**: Run on similar hardware/network
3. **Multiple runs**: Average results over multiple executions
4. **Resource monitoring**: Monitor CPU, memory, and network usage

## 🔍 Test Coverage

### Coverage Analysis

```bash
# Generate coverage report
pytest --cov=app --cov-report=html tests/

# View coverage report
open htmlcov/index.html
```

### Target Coverage Areas

- **Algorithm logic**: 100% coverage target
- **API endpoints**: 95% coverage target  
- **Database operations**: 90% coverage target
- **Error handling**: 100% coverage target

## 🚀 Advanced Testing

### Custom Test Scenarios

Create custom test combinations:

```bash
# Test specific scenarios
pytest -k "algorithm and basic" -v
pytest -k "integration or performance" -v
pytest -k "not slow" -v
```

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto tests/
```

### Continuous Testing

```bash
# Watch for file changes and re-run tests
pip install pytest-watch
ptw tests/
```

## 📞 Troubleshooting

### Common Issues

1. **Async fixture warnings**: Normal with pytest-asyncio, can be ignored
2. **Performance test failures**: Often due to system load, not code issues
3. **Integration test timeouts**: Check network connectivity and server status
4. **Unknown marker warnings**: Expected behavior, tests still run correctly

### Getting Help

- Review test output carefully for specific error messages
- Check server logs when integration tests fail
- Verify environment variables for database tests
- Consult individual test files for specific test requirements

### Test Development

For adding new tests or modifying existing ones:
1. Follow the existing patterns in `tests/` directory
2. Use appropriate markers for categorization
3. Add comprehensive docstrings
4. Include both positive and negative test cases
5. Update this documentation when adding new test categories