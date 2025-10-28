# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an SLR (Systematic Literature Review) automation web application that helps researchers automate parts of the research process. The application combines a Python Flask backend with a React frontend to generate research questions, search strings, fetch papers, filter them for relevance, and generate summaries.

## Development Commands

### Backend (Flask)
- **Start backend server**: `python server.py`
  - Runs on `localhost:5000`
  - Serves both API endpoints and the built React app in production

### Frontend (React)
- **Development mode**: `npm run dev`
  - Runs Vite dev server on `localhost:5173`
  - Proxies API calls to Flask backend at `localhost:5000`
- **Build for production**: `npm run build`
  - Creates optimized build in `dist/` directory
  - Flask serves this build in production
- **Lint code**: `npm run lint`
  - Uses ESLint to check JavaScript/JSX files
- **Preview production build**: `npm run preview`

### Python Dependencies
- **Install dependencies**: `pip install -r requirements.txt`
- **For deployment**: Use `requirements-deploy.txt` (optimized for cloud platforms)

## Architecture

### Backend Structure (Flask)
- **`server.py`**: Main Flask application with all API endpoints
- **`agents.py`**: OpenAI API integration for research questions, abstracts, introductions, conclusions
- **`agents2.py`**: Search string generation using LLM
- **`agents3.py`**: Paper fetching from academic databases (Scopus, Semantic Scholar, scholarly)
- **`agents4.py`**: Paper relevance filtering and response generation using LLM
- **`templates/latex_template.tex`**: LaTeX template for final summary document

### Frontend Structure (React + Vite + Ant Design)
- **`src/App.jsx`**: Main component managing state and user interactions
- **`src/columns.jsx`**: Table column definitions for research questions, papers, and answers
- **`src/FullPageLoader.jsx`**: Loading spinner component
- **`src/mysvg.jsx`**: Custom SVG icons

### Key Features
1. **Research Question Generation**: Generate multiple research questions with purposes based on objective
2. **Search String Creation**: Create academic database search strings
3. **Paper Fetching**: Query Scopus, Semantic Scholar, and Google Scholar
4. **Paper Filtering**: AI-powered relevance filtering
5. **Answer Generation**: Generate answers to research questions from selected papers
6. **Summary Generation**: Create abstracts, introductions, and conclusions
7. **LaTeX Export**: Export complete summary as LaTeX document

## Environment Variables Required

```
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
SCOPUS_API_KEY=your_scopus_key
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key
```

## Model Support
- **OpenAI**: GPT-3.5 Turbo, GPT-4 Turbo Preview
- **DeepSeek**: DeepSeek Chat, DeepSeek Coder
- Backend automatically routes requests based on model name prefix

## Development Workflow
1. Backend runs Flask server for API endpoints
2. Frontend development uses Vite proxy to communicate with Flask
3. Production build serves React app through Flask static file serving
4. All data flows through RESTful API endpoints in `server.py`

## File Structure Notes
- **`dist/`**: Production build output (created by `npm run build`)
- **`public/`**: Static assets for React app
- **`.env`**: Environment variables (not in repo, create locally)
- **`Procfile`**: Heroku deployment configuration
- **`runtime.txt`**: Python version specification for deployment

## Special Considerations
- Uses both OpenAI and DeepSeek APIs for different LLM capabilities
- Includes proxy support for web scraping (scholarly library)
- LaTeX template system for academic document generation
- CORS enabled for cross-origin requests during development
- Deployment optimized with separate requirements file