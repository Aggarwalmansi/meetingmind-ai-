from typing import TypedDict, Optional
class MeetingState(TypedDict, total=False):
    audio_url: str           # URL or local path to the audio file
    push_notion: bool        # whether to push action items to Notion
    transcript: Optional[str]   # filled by Transcription agent
    rag_context: Optional[str]
    summary: Optional[str]      # filled by Summarization agent
    action_items: Optional[list]# filled by Action Items agent
    sentiment: Optional[dict]   # filled by Sentiment agent
    report: Optional[str]       # filled by Synthesis agent