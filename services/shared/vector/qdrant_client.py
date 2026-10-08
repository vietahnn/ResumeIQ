from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter
from services.shared.config import settings


class QdrantVectorService:
    COLLECTION_RESUMES = "resumes"
    COLLECTION_CAREER_KNOWLEDGE = "career_knowledge"
    COLLECTION_JOB_POSTINGS = "job_postings"
    COLLECTION_CONVERSATION_SUMMARIES = "conversation_summaries"

    def __init__(self):
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        self.vector_size = settings.EMBEDDING_DIMENSION

    # Creates standard vector collections if they do not already exist
    def init_collections(self) -> None:
        collections = [
            self.COLLECTION_RESUMES,
            self.COLLECTION_CAREER_KNOWLEDGE,
            self.COLLECTION_JOB_POSTINGS,
            self.COLLECTION_CONVERSATION_SUMMARIES
        ]
        existing_collections = [c.name for c in self.client.get_collections().collections]

        for collection_name in collections:
            if collection_name not in existing_collections:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )

    def upsert_vectors(self, collection_name: str, points: List[PointStruct]) -> None:
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )

    # Performs cosine similarity search with optional metadata filtering
    def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 5,
        query_filter: Optional[Filter] = None
    ) -> List[Any]:
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter
            )
            return response.points
        return self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=query_filter
        )


qdrant_service = QdrantVectorService()
