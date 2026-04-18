import os, json, assemblyai as aai
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from .state import MeetingState
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
    """
    Uses Groq / Llama 3 to produce a crisp executive summary.
    """
    transcript = state.get('transcript', '')
    prompt = f"""
    You are a professional meeting analyst.
    Produce a concise executive summary of the following meeting transcript.
    Structure your output in three sections:
    1. OVERVIEW (2-3 sentences of what the meeting was about)
    2. KEY DECISIONS (bullet points, each starting with a verb)
    3. OPEN QUESTIONS (unresolved items that need follow-up)
    Transcript:
    {transcript}
    """
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