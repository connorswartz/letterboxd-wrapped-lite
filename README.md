# Letterboxd Wrapped Lite

A privacy-focused web application that creates Spotify Wrapped-style year-in-review analytics for Letterboxd users.

## 🎬 Features

- **RSS Feed Processing**: Analyzes public Letterboxd diary data
- **TMDB Integration**: Enriches movie data with metadata from The Movie Database
- **Privacy-First**: Session-based processing with no permanent user data storage
- **Interactive Stats**: Comprehensive viewing analytics and patterns
- **Shareable Cards**: Generate social media-ready year-in-review images

## 🏗️ Architecture

- **Backend**: FastAPI + SQLModel + SQLite
- **Frontend**: Next.js + Tailwind CSS (planned)
- **Database**: SQLite (development) / PostgreSQL (production)
- **External APIs**: TMDB API v3

## 🚀 Current Status

**Completed:**
- ✅ RSS ingestion and parsing
- ✅ Database models and relationships  
- ✅ Background task processing
- ✅ Session tracking and progress monitoring
- ✅ Error handling and validation

**In Progress:**
- 🔄 TMDB movie enrichment
- 🔄 Statistics computation engine
- 🔄 Frontend dashboard

## 🛠️ Development Setup

### Prerequisites
- Python 3.9+
- Poetry
- TMDB API key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/letterboxd-wrapped-lite.git
cd letterboxd-wrapped-lite
```

2. Set up the backend:
```bash
cd backend
poetry install
```

3. Configure environment variables:
```bash
cp .env.example .env
# Add your TMDB API key to .env
```

4. Run the development server:
```bash
poetry run uvicorn app.main:app --reload
```

5. Visit the API docs: http://localhost:8000/docs

## 📋 Usage

1. **RSS Ingestion**: POST to `/api/ingest/rss/{username}` with a Letterboxd username
2. **Check Status**: GET `/api/ingest/status/{session_id}` to monitor progress
3. **View Stats**: GET `/api/stats/{session_id}` once processing is complete

## 🏛️ Project Structure

```
letterboxd-wrapped-lite/
├── backend/
│   ├── app/
│   │   ├── routers/          # API route handlers
│   │   ├── services/         # Business logic
│   │   ├── models.py         # Database models
│   │   ├── database.py       # Database configuration
│   │   └── main.py          # FastAPI application
│   ├── pyproject.toml       # Python dependencies
│   └── .env                 # Environment variables
└── frontend/                # Next.js app (planned)
```

## 🔮 Planned Features

- CSV upload support for complete diary history
- TMDB movie enrichment with genres, directors, cast
- Advanced analytics (viewing streaks, mood analysis, seasonal patterns)
- Interactive frontend dashboard
- Shareable social media cards
- Export options (JSON, PDF)

## 📄 License

This project is for educational purposes. Built as a summer 2025 portfolio project.

## 🙏 Acknowledgments

- [Letterboxd](https://letterboxd.com/) for the inspiration and RSS feeds
- [The Movie Database (TMDB)](https://www.themoviedb.org/) for movie metadata
- [FastAPI](https://fastapi.tiangolo.com/) and [Next.js](https://nextjs.org/) communities