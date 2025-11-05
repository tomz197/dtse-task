# Testing

This project includes a comprehensive test suite using pytest.

## Running Tests

### Install test dependencies

```bash
pip install -r requirements-dev.txt
```

This will install both production dependencies and testing dependencies.

### Run all tests

```bash
pytest
```

### Run with coverage

```bash
pytest --cov=src --cov=main --cov-report=html
```

### Run specific test file

```bash
pytest tests/test_database.py
```

### Run specific test

```bash
pytest tests/test_database.py::TestDatabaseManager::test_create_api_token
```

### Run tests in verbose mode

```bash
pytest -v
```

## Test Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `temp_db` - Creates a temporary database for testing
- `db_manager_with_token` - Creates a database manager with a test token
- `mock_housing_model` - Mocks the HousingModel for testing
- `rate_limiter` - Creates a rate limiter instance for testing
- `app_client` - Creates a FastAPI test client
- `sample_housing_input` - Sample housing input data

## Writing New Tests

When adding new tests:

1. Add test files in the `tests/` directory
2. Use pytest fixtures from `conftest.py` when possible
3. Follow the existing test naming conventions
4. Add docstrings to describe what each test does

