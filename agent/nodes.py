import os, json, assemblyai as aai
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from .state import MeetingState
from rag.retriever import retrieve_context
from notion_client import Client as NotionClient
load_dotenv()
# Groq is our AI engine — fast and free on the developer tier
llm = ChatGroq(model='llama-3.1-8b-instant', temperature=0.3)
# Set AssemblyAI key
aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')


def transcribe_audio(state: MeetingState) -> dict:
    """
    Sends the audio file to AssemblyAI and returns the full transcript.
    Supports MP3, MP4, WAV, FLAC, M4A, and direct URLs.
    """
    audio_url = state['audio_url']
    config = aai.TranscriptionConfig(speaker_labels=True, speech_models=["universal-2"])
    transcriber = aai.Transcriber(config=config)
    transcript_obj = transcriber.transcribe(audio_url)
    if transcript_obj.status == aai.TranscriptStatus.error:
        return {'transcript': f'Transcription failed: {transcript_obj.error}'}
    # Build a speaker-labeled transcript string
    lines = []
    for utterance in transcript_obj.utterances:
        lines.append(f'Speaker {utterance.speaker}: {utterance.text}')
    return {'transcript': chr(10).join(lines)}

def summarize_meeting(state: MeetingState) -> dict:
    transcript = state.get('transcript', '')
    rag_context = state.get('rag_context', '')
    # Build the context section only if RAG found something
    context_section = ''
    if rag_context:
        context_section = f'''
        RELEVANT PAST MEETINGS FOR CONTEXT:
        {rag_context}
        Use the above past meetings to provide continuity. If today's meeting references
        something discussed before, note that connection explicitly.
        '''
    prompt = f'''
    You are a professional meeting analyst with access to historical context.
    {context_section}
    TODAY'S MEETING TRANSCRIPT:
    {transcript}
    Produce a structured executive summary with three sections:
    1. OVERVIEW — 2-3 sentences on what the meeting was about
    2. KEY DECISIONS — bullet points, each starting with a verb
    3. OPEN QUESTIONS — unresolved items needing follow-up
    '''
    response = llm.invoke([HumanMessage(content=prompt)])
    return {'summary': response.content}

def extract_action_items(state: MeetingState) -> dict:
    """
    Extracts structured action items with owner, deadline, and priority.Returns a list of dicts for easy rendering.
    """
    transcript = state.get('transcript', '')
    prompt = f"""
    You are an expert project coordinator. Extract every action item from this
    transcript.
    Return ONLY a valid JSON array. Each item must have these keys:
    - task: string (what must be done)
    - owner: string (the person responsible, or 'Unassigned')
    - deadline: string (mentioned date/timeframe, or 'Not specified')
    - priority: string ('High', 'Medium', or 'Low')
    Return only the JSON array. No markdown, no explanation.
    Transcript:
    {transcript}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        items = json.loads(response.content)
    except json.JSONDecodeError:
        items = [{'task': 'Could not parse action items', 'owner': '-',
    'deadline': '-', 'priority': '-'}]
    return {'action_items': items}

def analyze_sentiment(state: MeetingState) -> dict:
    """
    Detects emotional tone, risk signals, and participation balance.
    """
    transcript = state.get('transcript', '')
    prompt = f"""
    Analyze the sentiment and team dynamics in this meeting transcript.
    Return ONLY a valid JSON object with these keys:
    - overall_tone: 'Positive', 'Neutral', 'Tense', or 'Mixed'
    - risk_flags: list of strings (concerns, conflicts, confusion moments)
    - energy_level: 'High', 'Medium', or 'Low'
    - recommendation: one-sentence coaching note for the meeting facilitator
    Return only the JSON object. No markdown, no explanation.
    Transcript:
    {transcript}
    """
    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        sentiment = json.loads(response.content)
    except json.JSONDecodeError:
        sentiment = {'overall_tone': 'Unknown', 'risk_flags': [],
                     'energy_level': 'Unknown', 'recommendation': ''}
    return {'sentiment': sentiment}


def synthesize_report(state: MeetingState) -> dict:
    """
    Merges all agent outputs into a single clean markdown report string.
    The FastAPI endpoint will also return this as JSON.
    """
    summary = state.get('summary', 'No summary available.')
    items = state.get('action_items', [])
    sent = state.get('sentiment', {})
    items_text = '\n'.join(
        [f" [{i['priority']}] {i['task']} — {i['owner']} by {i['deadline']}"
         for i in items]
    ) or ' None identified.'
    report = f"""
    # MeetingMind AI Report

    ## Executive Summary
    {summary}

    ## Action Items
    {items_text}

    ## Sentiment Analysis
    - Overall tone: {sent.get('overall_tone', 'N/A')}
    - Energy level: {sent.get('energy_level', 'N/A')}
    - Risk flags: {', '.join(sent.get('risk_flags', [])) or 'None'}
    - Facilitator note: {sent.get('recommendation', 'N/A')}
    """
    return {'report': report.strip()}

def rag_context_node(state: MeetingState) -> dict:
    """
    Retrieves the top 3 most relevant past meeting summaries
    and stores them in state so other agents can use them.
    This node runs BEFORE summarization.
    """
    transcript = state.get('transcript', '')
    if not transcript:
        return {'rag_context': ''}
    # Use first 500 chars of transcript as search query
    query = transcript[:500]
    context = retrieve_context(query, n_results=3)
    return {'rag_context': context}

def push_to_notion(state: MeetingState) -> dict:
    """
    Pushes action items from the current meeting into a Notion database.
    Each action item becomes its own row in the database.
    This is an optional output node — it does not block the main pipeline.
    """
    if not state.get('push_notion', False):
        return {}

    notion_token = os.getenv('NOTION_TOKEN')
    notion_db_id = os.getenv('NOTION_DB_ID')
    if not notion_token or not notion_db_id:
        print('Notion credentials not found — skipping Notion push')
        return {}
    notion = NotionClient(auth=notion_token)
    items = state.get('action_items', [])
    today = __import__('datetime').date.today().isoformat()
    for item in items:
        try:
            notion.pages.create(
                parent={'database_id': notion_db_id},
                properties={
                    'Name': {
                        'title': [{'text': {'content': item.get('task', '')}}]
                    },
                    'Owner': {
                        'rich_text': [{'text': {'content': item.get('owner', 'Unassigned')}}]
                    },
                    'Deadline': {
                        'rich_text': [{'text': {'content': item.get('deadline', 'Not specified')}}]
                    },
                    'Priority': {
                        'select': {'name': item.get('priority', 'Medium')}
                    },
                    'Meeting Date': {
                        'date': {'start': today}
                    },
                    'Audio URL': {
                        'rich_text': [{'text': {'content': state.get('audio_url', '')}}]
                    },
                }
            )
        except Exception as e:
            print(f'[Notion] Push failed for item "{item.get("task", "")}" — {type(e).__name__}: {e}')
            continue  # never crash the pipeline over Notion
    return {}  # no state mutation needed