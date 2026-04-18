import chromadb
from chromadb.utils import embedding_functions
import os
# ChromaDB stores its data in a local folder — no external server needed
CHROMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'chroma_store')
# Use a free, local sentence-transformer model for embeddings
# This runs 100% locally — no API key, no cost
embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
model_name='all-MiniLM-L6-v2'
)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(
name='meeting_summaries',
embedding_function=embed_fn,
)
def index_meeting(meeting_id: int, summary: str, metadata: dict = None):
    """
    Converts the meeting summary to a vector and stores it.
    Call this every time you save a new meeting.
    """
    if not summary or not summary.strip():
        return
    collection.upsert(
    ids=[str(meeting_id)],
    documents=[summary],
    metadatas=[metadata or {}],
    )
def retrieve_context(query_text: str, n_results: int = 3) -> str:
    """
    Searches ChromaDB for the top n_results most similar past meetings.
    Returns a formatted string ready to inject into a prompt.
    """
    if collection.count() == 0:
        return '' # no past meetings yet — skip RAG
    results = collection.query(
    query_texts=[query_text],
    n_results=min(n_results, collection.count()),
    )
    documents = results.get('documents', [[]])[0]
    if not documents:
        return ''
    context_parts = []
    for i, doc in enumerate(documents, 1):
        context_parts.append(f'Past meeting {i}:\n{doc}')
    return '\n\n'.join(context_parts)