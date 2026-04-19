from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agent.graph import meeting_app
from db.database import init_db, save_meeting, get_all_meetings, search_meetings, get_meeting_by_id
from rag.retriever import index_meeting
from fastapi.responses import Response
from pdf_report.generator import generate_pdf

# Call init_db() when the app starts
init_db()

app = FastAPI(title='MeetingMind AI', version='1.0')

# Allow the Streamlit frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

class MeetingRequest(BaseModel):
    audio_url: str  # Can be a public URL or a file path

@app.get('/')
def home():
    return {'message': 'MeetingMind AI backend is running!'}

@app.post('/analyze')
def analyze_meeting(req: MeetingRequest,push_notion: bool = True):
    try:
        initial_state = {'audio_url': req.audio_url,'push_notion': push_notion,}
        result = meeting_app.invoke(initial_state)
        # Persist the result to SQLite
        result['audio_url'] = req.audio_url

        row_id = save_meeting(result)
        index_meeting(row_id, result.get('summary', '')) # index for RAG
        return {
            'meeting_id':   row_id,
            'transcript': result.get('transcript'),
            'summary': result.get('summary'),
            'action_items': result.get('action_items'),
            'sentiment': result.get('sentiment'),
            'report': result.get('report'),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/history')
def get_history():
    return get_all_meetings()

@app.get('/history/search')
def search_history(query: str):
    return search_meetings(query)

@app.get('/report/{meeting_id}')
def download_report(meeting_id: int):
    """
    Fetches a stored meeting by id and generates a PDF.
    Does NOT re-run the pipeline — analysis already happened via /analyze.
    """
    meeting = get_meeting_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail=f'Meeting {meeting_id} not found')

    # Deserialize JSON fields stored as strings in SQLite
    import json
    meeting['action_items'] = json.loads(meeting.get('action_items') or '[]')
    meeting['sentiment']    = json.loads(meeting.get('sentiment')    or '{}')

    pdf_bytes = generate_pdf(meeting)
    return Response(
        content=pdf_bytes,
        media_type='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=meeting_{meeting_id}_report.pdf'},
    )