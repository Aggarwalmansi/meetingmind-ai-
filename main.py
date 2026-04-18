from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agent.graph import meeting_app
from db.database import init_db, save_meeting, get_all_meetings, search_meetings
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

@app.post('/report')
def download_report(req: MeetingRequest):
    """
    Runs the full analysis and returns a PDF file directly.
    """
    try:
        initial_state = {'audio_url': req.audio_url}
        result = meeting_app.invoke(initial_state)
        result['audio_url'] = req.audio_url
        
        row_id = save_meeting(result)
        index_meeting(row_id, result.get('summary', ''))
        
        pdf_bytes = generate_pdf(result)
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': 'attachment; filename=meeting_report.pdf'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
