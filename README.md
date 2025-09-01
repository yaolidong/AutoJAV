# AV Metadata Scraper

A Docker-based automated video metadata scraping and organizing system for Japanese AV content.

## Features

- 🔍 **Multi-source scraping**: Supports JavDB, JavLibrary, and other sources
- 🤖 **Automated login**: Handles login with captcha support
- 📁 **Smart organization**: Organizes files by actress/code structure
- 🖼️ **Image download**: Downloads covers, posters, and screenshots
- 🐳 **Docker ready**: Easy deployment with Docker containers
- ⚡ **Concurrent processing**: Processes multiple files simultaneously
- 🔄 **Retry mechanism**: Robust error handling and retry logic

## Quick Start

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd av-metadata-scraper
```

2. Create your configuration:
```bash
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml with your settings
```

3. Run with Docker Compose:
```bash
docker-compose up -d
```

### Manual Installation

1. Install Python 3.9+ and dependencies:
```bash
pip install -r requirements.txt
```

2. Install Chrome/Chromium browser

3. Configure the application:
```bash
cp config/config.yaml.example config/config.yaml
# Edit config/config.yaml
```

4. Run the application:
```bash
python main.py
```

## Configuration

Edit `config/config.yaml` to configure:

- Source and target directories
- JavDB login credentials
- Scraper priorities and settings
- File naming patterns
- Browser and network settings

## Directory Structure

```
av-metadata-scraper/
├── src/                    # Source code
│   ├── models/            # Data models
│   ├── scrapers/          # Website scrapers
│   ├── scanner/           # File scanning
│   ├── organizer/         # File organization
│   ├── config/            # Configuration management
│   └── utils/             # Utility functions
├── tests/                 # Test files
├── config/                # Configuration files
├── docker/                # Docker files
├── logs/                  # Log files
├── requirements.txt       # Python dependencies
└── main.py               # Main entry point
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
```

## Documentation

### User Documentation
- **[User Guide](docs/USER_GUIDE.md)** - Complete installation and usage guide
- **[FAQ](docs/FAQ.md)** - Frequently asked questions and answers
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Docker Deployment Guide](DOCKER_DEPLOYMENT.md)** - Detailed Docker setup and management

### Configuration Examples
- **[Basic Configuration](docs/examples/basic-config.yaml)** - Simple setup for beginners
- **[Advanced Configuration](docs/examples/advanced-config.yaml)** - Full configuration with all options
- **[Docker Environment](docs/examples/docker-config.env)** - Docker environment variables
- **[Usage Scenarios](docs/examples/USAGE_SCENARIOS.md)** - Real-world setup examples

### Developer Documentation
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Contributing and development setup
- **[Architecture Overview](docs/API_DOCUMENTATION.md#architecture-overview)** - System design and components

## Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: Check the comprehensive documentation above
- **Community**: Join discussions and get help from other users

## License

This project is for educational purposes only. Please respect copyright laws and website terms of service.