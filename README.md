# YTSage — YouTube to Shorts Synthesis Agent

YTSage is a multi-agent AI system that transforms long-form YouTube lectures and tech talks into short-form educational infographic slideshows. Given a YouTube URL, it extracts the transcript, identifies key concepts, designs educational infographics, and stitches them into a video summary.

> This product is entirely derived from work conducted as part of the NUS CS5260 course.

## Architecture

```
User pastes YouTube URL (frontend)
        |
        v
Ingest Agent
  - Extract transcript (YouTube Transcript API, fallback to Whisper)
  - Semantic chunking + embed into ChromaDB vector store
        |
        v
Planner Agent (GPT-4o via Replicate)
  - RAG query on vector store for overview chunks
  - Identify top 3 concepts with timestamps
  - Attach relevant transcript segments to each concept
        |
        v
Script Writer Agent (GPT-4o via Replicate)
  - Design 2 infographic prompts per concept (overview + deep dive)
  - Grounded in actual transcript segments
        |
        v
Video Generator Agent (Nano Banana Pro via Replicate)
  - Generate 6 infographic images (2 per concept)
  - Stitch into a 30-second MP4 slideshow (ffmpeg)
        |
        v
Results Page — Infographic images, slideshow video, timestamp links
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| Agent Orchestration | LangGraph (directed state graph) |
| LLM | GPT-4o via Replicate |
| Image Generation | Google Nano Banana Pro via Replicate |
| Transcript Extraction | youtube-transcript-api + Whisper fallback |
| Vector Store | ChromaDB + OpenAI embeddings |
| Semantic Chunking | LangChain text splitters |
| Video Stitching | ffmpeg |
| Frontend | Next.js 16, TypeScript, Tailwind CSS |
| Caching | File-based (SHA256 by URL hash) |

### Multi-Agent Pipeline (LangGraph)

The system uses LangGraph to orchestrate 4 agents in sequence with error-safe conditional routing:

```
ingest --> planner --[ok]--> script_writer --[ok]--> video_generator --> END
                |                   |
                +--[error]-->END    +--[error]-->END
```

Each agent reads from and writes to a shared `YTSageState` (TypedDict), enabling structured data flow between stages.

## Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point + CORS + lifespan
│   │   ├── core/
│   │   │   ├── config.py           # Settings (API keys, cost limits, ChromaDB)
│   │   │   ├── logger.py           # Structured logging
│   │   │   └── prompts.py          # Centralized LLM prompts
│   │   ├── models/
│   │   │   ├── state.py            # LangGraph state (YTSageState)
│   │   │   ├── pipeline.py         # API request/response models
│   │   │   ├── ingestion.py        # Ingestion status + video metadata
│   │   │   └── chat.py             # Chat session models
│   │   ├── routes/
│   │   │   ├── pipeline.py         # /process, /status, /result, /slideshow
│   │   │   ├── ingestion.py        # /ingest endpoint
│   │   │   ├── chat.py             # Chat-with-video endpoints
│   │   │   └── debug.py            # Debug endpoints
│   │   ├── agents/
│   │   │   ├── graph.py            # LangGraph state graph
│   │   │   ├── ingest.py           # Transcript ingestion + vector store
│   │   │   ├── planner.py          # Concept ranking agent (GPT-4o via Replicate)
│   │   │   ├── script_writer.py    # Infographic prompt designer (GPT-4o via Replicate)
│   │   │   └── video_generator.py  # Image generation + slideshow (Nano Banana Pro + ffmpeg)
│   │   └── services/
│   │       ├── transcript.py       # YouTube transcript extraction + semantic chunking
│   │       ├── vector_store.py     # ChromaDB ingestion + retrieval
│   │       ├── cache.py            # File-based caching
│   │       ├── summary.py          # Video summarization
│   │       ├── conversation.py     # Chat-with-video service
│   │       └── infographic.py      # Pillow-based infographic fallback
│   ├── requirements.txt
│   ├── test_pipeline.py            # Step-by-step pipeline debugger
│   └── .env.example
├── frontend/
│   └── src/app/
│       ├── page.tsx                        # Landing page (URL input)
│       ├── layout.tsx                      # Root layout
│       ├── processing/[jobId]/page.tsx     # Processing page (progress steps)
│       └── results/[jobId]/page.tsx        # Results page (infographics + video)
├── Proposal.pdf
├── PLAN.md
└── README.md
```

## Frontend Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Landing | Paste a YouTube URL and submit. Redirects to processing page. |
| `/processing/[jobId]` | Processing | Polls `/api/status` every 3 seconds. Shows a 5-step progress indicator (ingesting, planning, designing, generating, done). Redirects to results on completion. |
| `/results/[jobId]` | Results | Displays concept cards with titles, descriptions, and timestamp links to the source video. Shows infographic images (click to enlarge) and an embedded slideshow video. |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/process` | Submit a YouTube URL — kicks off the full pipeline |
| GET | `/api/status/{job_id}` | Poll job status and progress |
| GET | `/api/result/{job_id}` | Get completed results (concepts, infographic URLs, slideshow) |
| GET | `/api/slideshow/{job_id}` | Serve the generated slideshow MP4 |
| GET | `/health` | Health check |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- ffmpeg (for video stitching)
- Replicate account with API token

### Backend Setup

**First time only:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys
```

**Run the server:**

```bash
./backend/run.sh
```

The backend runs at `http://localhost:8000`. Verify at `http://localhost:8000/health`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

### Running the Full App

```bash
# Terminal 1: Backend
cd backend && ./run.sh

# Terminal 2: Frontend
cd frontend && npm run dev
```

Open `http://localhost:3000`, paste a YouTube URL, and watch the pipeline run.

### Test the Pipeline Step-by-Step

```bash
cd backend
python test_pipeline.py 1    # Step 1: Extract transcript
python test_pipeline.py 2    # Step 2: Run planner
python test_pipeline.py 3    # Step 3: Run script writer
python test_pipeline.py 4    # Step 4: Generate infographics + slideshow
```

Each step saves its output to a JSON file (`test_output_N_*.json`). The next step loads from the previous step's output, so you can inspect and debug between steps.

| Step | Agent | What it does |
|------|-------|-------------|
| 1 | Transcript Service | Fetches the YouTube transcript using the YouTube Transcript API (with fallback to Whisper). Merges raw caption entries into ~60-second chunks. Saves to `test_output_1_transcript.json`. |
| 2 | Planner Agent (GPT-4o) | Sends the transcript to GPT-4o via Replicate. Identifies the top 3 key concepts with titles, descriptions, and timestamp ranges. Attaches relevant transcript segments to each concept. Saves to `test_output_2_planner.json`. |
| 3 | Script Writer Agent (GPT-4o) | Takes the 3 concepts and their transcript segments. Sends to GPT-4o via Replicate to design 2 infographic prompts per concept (overview slide + deep dive slide). Saves to `test_output_3_scripts.json`. |
| 4 | Video Generator (Nano Banana Pro) | Takes the 6 infographic prompts from step 3. Generates 6 infographic images using Google's Nano Banana Pro via Replicate. Downloads the images and stitches them into a single 30-second MP4 slideshow (5 seconds per slide) using ffmpeg. Saves to `test_output_4_videos.json`. |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `REPLICATE_API_TOKEN` | Replicate API token (for GPT-4o + Nano Banana Pro) | Yes |
| `OPENAI_API_KEY` | OpenAI API key (for embeddings + Whisper fallback) | Yes |
| `MAX_COST_PER_SESSION_SGD` | Cost limit per session (default: 8.0) | No |
| `CACHE_DIR` | Directory for cached results (default: ./cache) | No |

## Agents

### Ingest Agent
- **Input:** YouTube URL
- **Process:** Fetch transcript (caption API with English/translation/Whisper fallback), semantic chunking via LangChain, embed and store in ChromaDB
- **Output:** `video_id`, `transcript_chunks` with chunk indices

### Planner Agent
- **Model:** GPT-4o via Replicate
- **Input:** RAG query on ChromaDB for overview chunks (or raw transcript as fallback)
- **Output:** Top 3 concepts, each with title, description, timestamps, and relevant transcript segments
- **Cost:** ~$0.02 per call

### Script Writer Agent
- **Model:** GPT-4o via Replicate
- **Input:** Top 3 concepts with transcript segments
- **Output:** 2 infographic prompts per concept (overview + deep dive)
- **Cost:** ~$0.02 per call

### Video Generator Agent
- **Model:** Google Nano Banana Pro via Replicate
- **Input:** 6 infographic prompts from script writer
- **Output:** 6 infographic images + 1 stitched MP4 slideshow (30s, 5s per slide)
- **Cost:** ~$0.50 per run (6 images)

**Total estimated cost per run:** ~$0.55

## Course Relevance (CS5260)

This project incorporates concepts from multiple weeks of the CS5260 curriculum:

| Week | Topic | How it's used in YTSage |
|------|-------|------------------------|
| Week 1 | Transformers, MoE | Tested with 3Blue1Brown Attention video |
| Week 8 | Video Generation (DiT, Wan, Hunyuan) | Nano Banana Pro for infographic generation |
| Week 10 | LLM Agents (ReAct, AutoGen) | Multi-agent LangGraph pipeline with 4 agents |

## Cost Constraints

- Total API cost must stay under SGD 10 for testing
- Session aborts if estimated cost exceeds SGD 8
- All results cached by YouTube URL hash to avoid re-processing
- Estimated cost per run: ~$0.55

## Team

- Ronak Lakhotia (A0161401Y)
- Shivansh Srivastava (A0328697H)
