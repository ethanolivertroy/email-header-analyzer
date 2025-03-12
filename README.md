# E-Mail Header Analyzer (MHA)
![mha](https://cloud.githubusercontent.com/assets/1170490/18221866/b7b362d6-718e-11e6-9fa0-2e7f8bc2b9d7.png)

## What is E-Mail Header Analyzer (MHA)?
Email Header Analyzer is a tool written in [Flask](https://flask.palletsprojects.com/) for parsing email headers and converting them to a human-readable format. It provides:

* Email header visualization and analysis
* Hop delay identification and visualization
* Email source identification with geolocation
* Security header analysis (SPF, DKIM, DMARC, ARC)
* Detection of anomalies in email routing

## Features
* Modern Flask application with application factory pattern
* Robust error handling for malformed headers
* Improved security header analysis
* Enhanced visualization of email paths
* Geolocation of servers in the email path

## MHA is an alternative to:
| Name | Developer | Limitations |
| ---- | --- | ----- |
| [MessageHeader](https://toolbox.googleapps.com/apps/messageheader/) | Google | Limited hop visibility |
| [EmailHeaders](https://mxtoolbox.com/Public/Tools/EmailHeaders.aspx) | Mxtoolbox | Performance issues |
| [Message Header Analyzer](https://testconnectivity.microsoft.com/MHA/Pages/mha.aspx) | Microsoft | Interface limitations |

## Installation

### System Requirements
- Python 3.8 or higher
- pip and virtualenv

### Setup

1. Install system dependencies:
```bash
sudo apt-get update
sudo apt-get install python3-pip
sudo pip3 install virtualenv
```

2. Create a Python virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Clone the repository:
```bash
git clone https://github.com/lnxg33k/email-header-analyzer.git
cd email-header-analyzer
```

4. Install Python dependencies:
```bash
pip install -r requirements.txt
```

5. Run the development server:
```bash
# Run with default settings (localhost:8080)
python -m mha.server

# Run with debugging enabled
python -m mha.server -d

# Specify binding address and port
python -m mha.server -b 0.0.0.0 -p 5000
```

6. Visit [http://localhost:8080](http://localhost:8080) in your browser.

## Docker

A `Dockerfile` is provided for containerized deployment:

```bash
# Build the Docker image
docker build -t mha:latest .

# Run a container
docker run -d -p 8080:8080 mha:latest
```

### Docker Compose

Use the provided `docker-compose.yml` file for easier deployment:

```bash
# Start the application
docker-compose up -d

# Stop the application
docker-compose down
```

To enable debugging, add this line to your `docker-compose.yml` file:
```yaml
command: --debug
```

## API Usage (Coming Soon)
In a future release, MHA will expose an API endpoint for programmatic access to email header analysis.

## Updates (2025)
- Modernized Flask application structure with application factory pattern
- Improved error handling and logging
- Enhanced security header analysis (added DMARC, ARC support)
- Updated dependencies to current versions
- Improved UI with better explanation of email routing
