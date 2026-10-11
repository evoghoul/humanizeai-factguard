# HumanizeAI — Context-Aware Writing & FactGuard

This is the backend for the HumanizeAI project, built with FastAPI. It provides endpoints to analyze text for robotic phrasing, humanize it using different tones and strengths, and validate the rewritten text to ensure factual consistency.

## Project Structure

```text
humanizeai-factguard/
├── backend/          # FastAPI backend (API, FactGuard engine, tests)
└── FRONTEND/         # React + Vite writing workspace & verification UI
```

## Backend Setup & Instructions

1. **Install Python**: Make sure you have Python 3.12 installed on your computer.
2. **Open Terminal & Navigate to Backend**:
   ```bash
   cd backend
   ```
3. **Create a Virtual Environment**: This keeps the project dependencies isolated. Run:
   ```bash
   python -m venv venv
   ```
4. **Activate the Virtual Environment**:
   - On Windows: `venv\Scripts\activate`
   - On Mac/Linux: `source venv/bin/activate`
5. **Install Dependencies**: Run this to install FastAPI and other required packages:
   ```bash
   pip install -r requirements.txt
   ```
6. **Set up Configuration**: Copy `.env.example` to `.env`. This holds your environment variables.
   - On Windows: `copy .env.example .env`
   - On Mac/Linux: `cp .env.example .env`

### Running the Backend

From the `backend` folder:
```bash
uvicorn app.main:app --reload
```
You should see a message saying the server is running on `http://127.0.0.1:8000`.

### Testing the API

- Go to `http://127.0.0.1:8000/docs` in your browser to view the interactive Swagger UI.

### Running Automated Backend Tests

From the `backend` folder:
```bash
pytest
```
This tests all endpoints and FactGuard validation logic.

## Starting the Frontend

The `FRONTEND` workspace connects to the FastAPI backend at `http://127.0.0.1:8000`.

1. **Open a New Terminal**: Keep the backend running in the first terminal, and open a new one.
2. **Navigate to the frontend folder**:
   ```bash
   cd FRONTEND
   ```
3. **Start the Development Server**:
   ```bash
   npm run dev
   ```
4. **Open the Website**:
   Open the displayed URL (e.g., [http://localhost:5173](http://localhost:5173) or [http://localhost:8443](http://localhost:8443)) in your web browser. You can write, humanize, and verify text with FactGuard protecting your facts and numbers!

