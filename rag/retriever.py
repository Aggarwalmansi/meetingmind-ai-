import chromadb
import os

CHROMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'chroma_store')

_client = None
_collection = None

def _get_collection():
    """
    Lazy-initializes ChromaDB client and collection on first use.
    Uses chromadb's built-in ONNX embedder — no PyTorch, no sentence-transformers.
    Safe to call at module import time; actual model loads only on first real request.
    """
    global _client, _collection
    if _collection is not None:
        return _collection

    from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
    embed_fn = ONNXMiniLM_L6_V2()

    _client = chromadb.PersistentClient(path=CHROMA_PATH)
    _collection = _client.get_or_create_collection(
        name='meeting_summaries',
        embedding_function=embed_fn,
    )
    return _collection
def index_meeting(meeting_id: int, summary: str, metadata: dict = None):
    """
    Converts the meeting summary to a vector and stores it.
    Call this every time you save a new meeting.
    """
    if not summary or not summary.strip():
        return
    collection = _get_collection()
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
    collection = _get_collection()
    if collection.count() == 0:
        return ''

    results = collection.query(
        query_texts=[query_text],
        n_results=min(n_results, collection.count()),
    )
    documents = results.get('documents', [[]])[0]
    if not documents:
        return ''

    return '\n\n'.join(
        f'Past meeting {i}:\n{doc}' for i, doc in enumerate(documents, 1)
    )