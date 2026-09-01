# PatternGenesis

PatternGenesis is a computational design and pattern-analysis platform focused on Kolam and extensible design grammars.

## Quick start

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

### Verify locally

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q

cd ..\frontend
npm run build
```

## Features

- Kolam image upload and preprocessing
- dot grid detection
- geometric primitive extraction
- symmetry and repetition detection
- grammar-based reconstruction
- React Konva editor and comparison view
- SQLite-backed design library
- 3D mesh export and viewer
- API-first architecture with optional AI service abstraction

## Architecture

- Frontend: Next.js + TypeScript + Tailwind + React Konva
- Backend: FastAPI + Pydantic + SQLModel + SQLite
- Computer vision: OpenCV + scikit-image
- Geometry: NumPy + SciPy + SymPy + Shapely + NetworkX
- 3D: trimesh + Three.js + React Three Fiber

## Development notes

This repository follows the requested monorepo structure and keeps the universal grammar separate from Kolam-specific logic.

## Planned and implemented scope

The initial release includes a working FastAPI foundation, data models, core processing services, and a frontend shell. The geometry pipeline is intentionally deterministic and designed to be extended with additional traditional pattern systems.
