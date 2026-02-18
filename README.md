# Jokelingo

Jokelingo is a platform for learning a new language while having fun.

## Prerequisites

- Python 3.8 or higher
- Pip (Python package manager)

## Setup

1. **Clone or navigate to the project directory:**
   ```bash
   cd jokelingo
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

4. **Run database migrations:**
   ```bash
   python3 manage.py migrate
   ```

5. **Set environment variables for local development:**
   ```bash
   export DEBUG=True
   export DATABASE_URL=postgresql://postgres:secret123@localhost:5432/postgres
   ```

## Running the Server

Start the Django development server:

```bash
python3 manage.py runserver
```

The server will start on `http://localhost:8000` by default.

To use a different port:

```bash
python3 manage.py runserver 8080
```
