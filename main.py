from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agent.graph import meeting_app
app = FastAPI(title='MeetingMind AI', version='1.0')
# Allow the Streamlit frontend to call this API
app.add_middleware(
CORSMiddleware,
allow_origins=['*'],
allow_methods=['*'],
allow_headers=['*'],
)
class MeetingRequest(BaseModel):
    audio_url: str # Can be a public URL or a file path
@app.get('/')
def home():
    return {'message': 'MeetingMind AI backend is running!'}
@app.post('/analyze')
def analyze_meeting(req: MeetingRequest):
    try:
        initial_state = {'audio_url': req.audio_url}
        result = meeting_app.invoke(initial_state)
        return {
        'transcript': result.get('transcript'),
        'summary': result.get('summary'),
        'action_items': result.get('action_items'),
        'sentiment': result.get('sentiment'),
        'report': result.get('report'),
}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))