# Student Study Planner (Flask + Docker)

A Flask web app for planning school work with:
- Subjects and weekly hour goals
- Deadlines with priority labels
- Study blocks on a timeline board
- Per-subject progress bars

## Run Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 app.py
```

Open `http://127.0.0.1:5000`.

## Docker (Single Container)

```bash
# Build image
docker build -t study-planner .

# Run container with persistent DB volume
docker run -d \
  --name study-planner \
  -p 5000:5000 \
  -v planner_data:/data \
  study-planner
```

Open `http://localhost:5000`.

### Docker Commands

```bash
# View logs
docker logs -f study-planner

# Stop/remove container
docker stop study-planner
docker rm study-planner

# Remove image
docker rmi study-planner

# Remove named volume (deletes app data)
docker volume rm planner_data
```

## Data Persistence

The app uses SQLite and reads `PLANNER_DB_PATH`.
- Local default: `./planner.db`
- Docker default: `/data/planner.db` (mounted to `planner_data` volume)
