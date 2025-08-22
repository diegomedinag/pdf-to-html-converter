# PDF to HTML Converter with AI-Powered Iterative Refinement

A sophisticated web application that converts PDF documents to HTML with exceptional visual fidelity using Google's Gemini AI and iterative screenshot-based refinement.

![Project Banner](https://img.shields.io/badge/AI%20Powered-PDF%20to%20HTML-blue?style=for-the-badge&logo=google&logoColor=white)
![Version](https://img.shields.io/badge/Version-1.0.0-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

## 🚀 Key Features

### Advanced AI-Powered Conversion
- **Gemini 1.5 Pro Integration**: Utilizes Google's latest AI model for intelligent HTML generation
- **Iterative Refinement**: Automatically improves output quality through screenshot comparison
- **High Visual Fidelity**: Achieves pixel-perfect reproduction of PDF layouts and formatting

### Real-Time Processing
- **WebSocket Integration**: Live progress updates during conversion
- **Page-by-Page Processing**: Process and preview individual pages as they complete
- **Interactive Progress Tracking**: Detailed logs and quality metrics for each page

### User-Friendly Interface
- **Drag & Drop Upload**: Intuitive file upload with validation
- **Live Preview**: Real-time HTML preview as pages are processed
- **Multi-Format Export**: Download combined HTML or individual pages
- **Responsive Design**: Works seamlessly on desktop and mobile devices

### Production-Ready Architecture
- **Docker Containerization**: Easy deployment with Docker Compose
- **Nginx Proxy Manager Support**: Built-in support for reverse proxy setups
- **Health Monitoring**: Comprehensive health checks and error handling
- **Scalable Backend**: FastAPI with async processing capabilities

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   React Frontend│    │  FastAPI Backend │    │  Gemini AI API     │
│   (Vite + Nginx)│◄──►│  (Python 3.13)  │◄──►│  (Vision Model)    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
         │                       │                        
         │              ┌──────────────────┐              
         └──────────────►│  Playwright      │              
                         │  (Screenshots)   │              
                         └──────────────────┘              
                                  │                        
                         ┌──────────────────┐              
                         │  PyMuPDF         │              
                         │  (PDF Processing)│              
                         └──────────────────┘              
```

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **Python 3.13**: Latest Python with enhanced async capabilities
- **PyMuPDF**: High-performance PDF processing and rendering
- **Google Generative AI**: Gemini 1.5 Pro for HTML generation
- **Playwright**: Headless browser automation for screenshots
- **WebSockets**: Real-time bidirectional communication

### Frontend
- **React 18**: Modern UI library with hooks and concurrent features
- **Vite**: Lightning-fast build tool and dev server
- **Axios**: HTTP client for API communication
- **CSS3**: Modern styling with flexbox and grid layouts
- **WebSocket API**: Native WebSocket implementation

### Infrastructure
- **Docker & Docker Compose**: Containerization and orchestration
- **Nginx**: High-performance web server and reverse proxy
- **Playwright Browser**: Chromium for consistent screenshot rendering

## 📋 Prerequisites

Before installing, ensure you have:

- **Docker Desktop** (20.10.0 or later)
- **Docker Compose** (2.0.0 or later)
- **Google AI API Key** (for Gemini access)
- **4GB RAM minimum** (8GB recommended)
- **2GB disk space** for Docker images and temporary files

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-username/pdf-to-html-converter.git
cd pdf-to-html-converter

# Create environment file
cp backend/.env.example backend/.env
# Edit backend/.env and add your Gemini API key
```

### 2. Configure Environment

Edit `backend/.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
UPLOAD_DIR=./uploads
TEMP_DIR=./temp
SCREENSHOTS_DIR=./screenshots
MAX_FILE_SIZE=52428800  # 50MB
API_RATE_LIMIT_SECONDS=5
MAX_REFINEMENT_ITERATIONS=2
```

### 3. Launch with Docker

```bash
# Build and start all services
docker-compose up -d --build

# View logs (optional)
docker-compose logs -f
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs

## 🔧 Development Setup

For local development without Docker:

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 📡 API Documentation

### Upload PDF
```http
POST /api/convert
Content-Type: multipart/form-data

file: PDF file (max 50MB)
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "message": "PDF uploaded successfully",
  "websocket_url": "/ws/{task_id}",
  "filename": "document.pdf"
}
```

### WebSocket Connection
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/${taskId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress update:', data);
};
```

**WebSocket Message Types:**
- `connection`: Initial connection confirmation
- `progress`: General progress updates
- `page_completed`: Individual page completion with HTML
- `task_completed`: Final completion with combined HTML
- `error`: Error notifications

### Download Converted HTML
```http
GET /api/download/{task_id}
```

Returns the converted HTML file as a download.

### Check Task Status
```http
GET /api/status/{task_id}
```

**Response:**
```json
{
  "task_id": "uuid-string",
  "status": "completed",
  "filename": "document.pdf",
  "websocket_connected": false,
  "result_available": true
}
```

## 🐳 Docker Deployment

### Standard Deployment

```bash
# Clone and configure
git clone <repository-url>
cd pdf-to-html-converter

# Configure environment
cp backend/.env.example backend/.env
# Add your Gemini API key to backend/.env

# Deploy
docker-compose up -d --build
```

### Production Deployment with Nginx Proxy Manager

1. **Ensure NPM Network Exists:**
```bash
docker network create npm_default
```

2. **Update Environment Variables:**
```env
# In docker-compose.yml, adjust platform if needed:
platform: linux/arm64  # For ARM systems
platform: linux/amd64  # For x86 systems
```

3. **Deploy:**
```bash
docker-compose up -d --build
```

4. **Configure in Nginx Proxy Manager:**
   - **Domain**: your-domain.com
   - **Forward Hostname**: `pdf-to-html-converter-frontend`
   - **Forward Port**: `80`
   - **WebSocket Support**: ✅ Enabled
   - **SSL**: Configure as needed

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google AI API key for Gemini | Required |
| `MAX_FILE_SIZE` | Maximum PDF file size in bytes | 52428800 (50MB) |
| `API_RATE_LIMIT_SECONDS` | Delay between Gemini API calls | 5 |
| `MAX_REFINEMENT_ITERATIONS` | Max refinement cycles per page | 2 |

## 🔍 The Iterative Refinement Process

Our innovative conversion process ensures maximum visual fidelity:

### Step 1: PDF Extraction
- Extract each PDF page as a high-resolution PNG image (300 DPI)
- Preserve original dimensions and color accuracy
- Store metadata for optimal processing

### Step 2: Initial HTML Generation
- Send page image to Gemini 1.5 Pro with specialized prompts
- Generate semantic HTML5 with embedded CSS
- Focus on structural accuracy and content preservation

### Step 3: Visual Validation
- Render generated HTML using Playwright's Chromium engine
- Capture screenshot at exact original dimensions
- Prepare for visual comparison

### Step 4: AI-Powered Refinement
- Send both original PDF image and HTML screenshot to Gemini
- AI analyzes visual differences and layout discrepancies
- Generate improved HTML addressing identified issues

### Step 5: Quality Assessment
- Repeat refinement cycle up to configured maximum iterations
- Track quality improvements and processing metrics
- Deliver final optimized HTML

## 🧪 Testing

### Run Backend Tests

```bash
cd backend
python -m pytest tests/ -v
```

### Test Coverage Areas

- PDF processing and validation
- Gemini API integration (with mocks)
- WebSocket communication
- File upload and validation
- Error handling and edge cases

### Manual Testing

1. **Upload Test**: Try various PDF types and sizes
2. **WebSocket Test**: Monitor real-time progress updates
3. **Quality Test**: Compare output visual fidelity
4. **Error Handling**: Test with invalid files and network issues

## 🚨 Troubleshooting

### Common Issues

**Gemini API Errors:**
```bash
# Check API key configuration
docker-compose logs pdf-to-html-converter-backend | grep GEMINI
```

**WebSocket Connection Issues:**
- Ensure ports 8000 and 3000 are available
- Check firewall settings
- Verify Docker network configuration

**Playwright Browser Issues:**
```bash
# Rebuild with fresh browsers
docker-compose build --no-cache pdf-to-html-converter-backend
```

**Memory Issues:**
- Increase Docker Desktop memory allocation (8GB recommended)
- Reduce `MAX_REFINEMENT_ITERATIONS` for large documents

### Performance Tuning

**For Large PDFs:**
```env
MAX_REFINEMENT_ITERATIONS=1  # Reduce iterations
API_RATE_LIMIT_SECONDS=3     # Faster API calls (if quota allows)
```

**For Better Quality:**
```env
MAX_REFINEMENT_ITERATIONS=3  # More refinement cycles
API_RATE_LIMIT_SECONDS=5     # Respect rate limits
```

## 📈 Performance Metrics

### Typical Processing Times
- **Simple text PDF (5 pages)**: ~2-3 minutes
- **Complex layout PDF (10 pages)**: ~5-7 minutes  
- **Image-heavy PDF (20 pages)**: ~10-15 minutes

### Resource Requirements
- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB optimal
- **Storage**: 2GB for images + temporary files
- **Network**: Stable connection for Gemini API

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Commit: `git commit -m 'Add amazing feature'`
5. Push: `git push origin feature/amazing-feature`
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Google AI Team** - For the incredible Gemini API
- **PyMuPDF Team** - For robust PDF processing capabilities
- **Playwright Team** - For reliable browser automation
- **FastAPI Team** - For the excellent async web framework
- **React Team** - For the powerful UI library

## 📞 Support

- **Documentation**: Check this README and API docs
- **Issues**: [GitHub Issues](https://github.com/your-username/pdf-to-html-converter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/pdf-to-html-converter/discussions)

---

**Built with ❤️ using AI-powered iterative refinement**
