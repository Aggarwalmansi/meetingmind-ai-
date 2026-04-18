from typing import TypedDict, Optional
class MeetingState(TypedDict):
    audio_url: str # URL or local path to the audio file
    transcript: Optional[str] # filled by Transcription agent
    rag_context: Optional[str]
    summary: Optional[str] # filled by Summarization agent
    action_items: Optional[list] # filled by Action Items agent
    sentiment: Optional[dict] # filled by Sentiment agent
    report: Optional[str] # filled by Synthesis agent