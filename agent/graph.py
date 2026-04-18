from langgraph.graph import StateGraph, START, END
from .state import MeetingState
from .nodes import (
transcribe_audio,
rag_context_node,
summarize_meeting,
extract_action_items,
analyze_sentiment,
synthesize_report,
push_to_notion,
)
# build the graph
builder = StateGraph(MeetingState)
# Register every node
builder.add_node('transcribe', transcribe_audio)
builder.add_node('rag', rag_context_node)
builder.add_node('summarize', summarize_meeting)
builder.add_node('action_items', extract_action_items)
builder.add_node('sentiment', analyze_sentiment)
builder.add_node('synthesize', synthesize_report)
builder.add_node('notion', push_to_notion)
# Transcription runs first — all others depend on the transcript
builder.add_edge(START, 'transcribe')
builder.add_edge('transcribe', 'rag') # ← transcribe → RAG
builder.add_edge('rag', 'summarize') # ← RAG → summarize
builder.add_edge('transcribe', 'action_items')
builder.add_edge('transcribe', 'sentiment')
builder.add_edge('summarize', 'synthesize')
builder.add_edge('action_items', 'synthesize')
builder.add_edge('sentiment', 'synthesize')
builder.add_edge('synthesize', 'notion') # ← ADD
builder.add_edge('notion', END) 
meeting_app = builder.compile()
# Compile into a runnable app
