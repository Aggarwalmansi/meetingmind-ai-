from langgraph.graph import StateGraph, START, END
from .state import MeetingState
from .nodes import (
transcribe_audio,
summarize_meeting,
extract_action_items,
analyze_sentiment,
synthesize_report,
)
# build the graph
builder = StateGraph(MeetingState)
# Register every node
builder.add_node('transcribe', transcribe_audio)
builder.add_node('summarize', summarize_meeting)
builder.add_node('action_items', extract_action_items)
builder.add_node('sentiment', analyze_sentiment)
builder.add_node('synthesize', synthesize_report)
# Transcription runs first — all others depend on the transcript
builder.add_edge(START, 'transcribe')
# Analysis agents run sequentially, each adding to the shared state
builder.add_edge('transcribe', 'summarize')
builder.add_edge('summarize', 'action_items')
builder.add_edge('action_items', 'sentiment')
# Synthesis merges all results into the final report
builder.add_edge('sentiment', 'synthesize')
builder.add_edge('synthesize', END)
# Compile into a runnable app
meeting_app = builder.compile()