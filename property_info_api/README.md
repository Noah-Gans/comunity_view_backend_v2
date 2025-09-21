# Property Info API

A FastAPI-based service for scraping property information from various county websites. The API supports multiple counties including Teton, Sublette, Fremont, and Lincoln counties.

## Features

- **Multi-county support**: Scrape data from Teton, Sublette, Fremont, and Lincoln counties
- **Multiple data types**: Extract tax information, clerk records, and property details
- **Flexible scraping**: Support for individual or combined data extraction
- **Robust error handling**: Graceful fallbacks and validation
- **Fast performance**: Optimized for quick response times
- **Comprehensive testing**: Full test suite included

## Supported Counties

| County | Tax Data | Clerk Records | Property Details |
|--------|----------|---------------|------------------|
| Teton (WY) | ✅ | ✅ | ✅ |
| Sublette | ✅ | ✅ | ✅ |
| Fremont | ✅ | ✅ | ✅ |
| Lincoln | ✅ | ✅ | ✅ |

## Quick Start

### Prerequisites

- Python 3.9+
- pip

### Installation

1. **Clone the repository** (if not already done):
   ```bash
   cd property_info_api
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the API

1. **Start the API server**:
   ```bash
   source venv/bin/activate
   python main.py
   ```

2. **Access the API**:
   - API will be available at: `http://localhost:8001`
   - Interactive documentation: `http://localhost:8001/docs`
   - Alternative documentation: `http://localhost:8001/redoc`

## API Usage

### Endpoint: `/scrape`

**Method**: `POST`

**Request Body**:
```json
{
  "county": "teton",
  "links": {
    "tax": "https://tetoncountywy.gov/tax-example",
    "clerk": "https://tetoncountywy.gov/clerk-example",
    "property_details": "https://tetoncountywy.gov/property-example"
  }
}
```

**Parameters**:
- `county` (required): County name (e.g., "teton", "sublette", "fremont", "lincoln")
- `links` (required): Object containing URLs for different data types
  - `tax`: URL for tax information (optional)
  - `clerk`: URL for clerk records (optional)
  - `property_details`: URL for property details (optional)

**Response**:
```json
{
  "tax": {
    "tax_year": "2024",
    "assessed_value": "$500,000",
    "tax_amount": "$3,500",
    "due_date": "2024-12-31"
  },
  "clerk": {
    "recording_date": "2024-01-15",
    "document_type": "Warranty Deed",
    "book_page": "1234-567",
    "grantor": "John Smith",
    "grantee": "Jane Doe"
  },
  "property_details": {
    "county_parcel_id": "12345",
    "physical_address": "123 Main St",
    "owner_name": "John Smith",
    "total_acres": "5.2"
  }
}
```

### Example Requests

#### Scrape Tax Information Only
```bash
curl -X POST "http://localhost:8001/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "county": "teton",
    "links": {
      "tax": "https://tetoncountywy.gov/tax-example",
      "clerk": null,
      "property_details": null
    }
  }'
```

#### Scrape All Available Data
```bash
curl -X POST "http://localhost:8001/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "county": "sublette",
    "links": {
      "tax": "https://sublette.example.com/tax",
      "clerk": "https://sublette.example.com/clerk",
      "property_details": "https://sublette.example.com/property"
    }
  }'
```

#### Scrape Mixed Data Types
```bash
curl -X POST "http://localhost:8001/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "county": "fremont",
    "links": {
      "tax": "https://fremont.example.com/tax",
      "clerk": null,
      "property_details": "https://fremont.example.com/property"
    }
  }'
```

## Testing

### Run Simple Tests
```bash
source venv/bin/activate
python run_tests.py
```

### Run Full Test Suite with pytest
```bash
source venv/bin/activate
pytest test_api.py -v
```

### Test Specific Functionality
```bash
# Test only tax scraping
pytest test_api.py::TestPropertyInfoAPI::test_scrape_endpoint_teton_tax -v

# Test performance
pytest test_api.py::TestAPIPerformance -v
```

## Configuration

The API configuration is managed in `config.py`:

- **Environment**: Set `ENVIRONMENT` variable to switch between development and production
- **Database paths**: Configure database and data directory paths
- **API settings**: Customize host, port, and worker settings
- **Logging**: Adjust log level and format

### Environment Variables

```bash
export ENVIRONMENT=production
export API_HOST=0.0.0.0
export API_PORT=8000
export LOG_LEVEL=INFO
```

## Architecture

### Core Components

1. **Main API** (`main.py`): FastAPI application with endpoint definitions
2. **Parsers** (`parsers/`): County-specific data extraction logic
3. **General Parsers** (`general_parsers/`): Shared parsing functionality
4. **Overrides** (`overrides/`): County-specific customizations
5. **Configuration** (`config.py`): Environment and settings management

### Data Flow

1. **Request**: Client sends POST request with county and URLs
2. **Routing**: API routes to appropriate parser based on county
3. **Scraping**: Parser extracts data from provided URLs
4. **Processing**: Data is normalized and structured
5. **Response**: Structured data is returned to client

### Extending the API

#### Adding a New County

1. **Create parser file** in `parsers/` directory
2. **Implement scraping logic** for the new county
3. **Add county mapping** in the appropriate parser
4. **Update tests** to include the new county

#### Adding New Data Types

1. **Extend the request model** in `main.py`
2. **Create parser functions** for the new data type
3. **Update response structure** to include new fields
4. **Add validation** and error handling

## Troubleshooting

### Common Issues

1. **API not starting**:
   - Check if port 8001 is available
   - Verify virtual environment is activated
   - Check Python version compatibility

2. **Import errors**:
   - Ensure virtual environment is activated
   - Verify all dependencies are installed
   - Check Python path

3. **Scraping failures**:
   - Verify URLs are accessible
   - Check county parameter spelling
   - Review parser error logs

### Debug Mode

Enable debug logging by setting:
```bash
export LOG_LEVEL=DEBUG
```

### Logs

The API generates logs for:
- Request/response details
- Scraping operations
- Error conditions
- Performance metrics

## Performance

- **Response Time**: Typically < 1 second for single requests
- **Concurrent Requests**: Supports multiple simultaneous requests
- **Memory Usage**: Optimized for minimal memory footprint
- **Scalability**: Designed for horizontal scaling

## Security

- **Input Validation**: All inputs are validated using Pydantic
- **CORS**: Configured for cross-origin requests
- **Error Handling**: Secure error messages without information leakage
- **Rate Limiting**: Built-in request throttling

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make your changes**
4. **Add tests** for new functionality
5. **Run the test suite**
6. **Submit a pull request**

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions or issues:
1. Check the documentation at `/docs` endpoint
2. Review the test suite for usage examples
3. Check the logs for error details
4. Open an issue in the repository

## Changelog

### Version 1.0.0
- Initial release
- Support for 4 counties
- Tax, clerk, and property details scraping
- Comprehensive test suite
- FastAPI-based REST API
