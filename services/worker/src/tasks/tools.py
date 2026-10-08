import logging
from typing import Dict, Any, Tuple, Optional, List
from services.shared.config import settings

logger = logging.getLogger("ToolsTask")


class ToolsTask:
    # Searches and aggregates matching job postings and market intelligence via Tavily or curated fallback
    @classmethod
    async def execute(cls, payload: Dict[str, Any], resume_id: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
        query = payload.get("user_query", "Software Engineer")
        target_role = payload.get("target_role") or "Backend / AI Developer"

        # 1. Real web search via official TavilyClient SDK if API key is provided
        if settings.TAVILY_API_KEY:
            try:
                from tavily import AsyncTavilyClient
                tavily_client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
                search_query = f"tuyển dụng {target_role} {query} hiring 2026"
                response = await tavily_client.search(
                    query=search_query,
                    search_depth="basic",
                    max_results=5,
                    include_answer=False
                )
                results = response.get("results", []) if isinstance(response, dict) else getattr(response, "results", [])
                if results:
                            cards = []
                            for idx, item in enumerate(results, 1):
                                title = item.get("title", f"Vị trí {target_role}")
                                url = item.get("url", "#")
                                snippet = item.get("content", "").strip()[:200]
                                cards.append(
                                    f"#### {idx}. [{title}]({url})\n"
                                    f"- **Thông tin tóm tắt:** {snippet}...\n"
                                    f"- [Xem chi tiết bài tuyển dụng]({url})"
                                )

                            markdown_body = (
                                f"### Kết Quả Tìm Kiếm Việc Làm Qua Tavily AI ('{search_query}')\n\n"
                                + "\n\n".join(cards)
                                + "\n\n*Dữ liệu được tìm kiếm và lọc trực tiếp từ Internet thông qua Tavily Search SDK.*"
                            )
                            return markdown_body, {
                                "source": "tavily",
                                "jobs": results,
                                "items": results,
                                "total_found": len(results)
                            }
            except Exception as exc:
                logger.warning("Tavily API call failed, falling back to curated jobs: %s", exc)

        # 2. Curated partner and market fallback jobs
        sample_jobs = [
            {
                "title": f"Senior {target_role}",
                "company": "VNG Corporation",
                "location": "Ho Chi Minh City / Hybrid",
                "salary": "$2,500 - $3,500",
                "match_rate": "92%",
                "tags": ["Python", "FastAPI", "Kafka", "Docker"],
                "apply_url": "https://careers.vng.com.vn"
            },
            {
                "title": f"AI Platform Engineer ({target_role})",
                "company": "FPT Software AI Center",
                "location": "Hanoi / Remote",
                "salary": "$2,000 - $3,000",
                "match_rate": "87%",
                "tags": ["Qdrant", "LangChain", "LLM", "Microservices"],
                "apply_url": "https://fptsoftware.com/careers"
            },
            {
                "title": "Backend Microservices Architect",
                "company": "MoMo (M_Service)",
                "location": "Ho Chi Minh City",
                "salary": "$3,000 - $4,200",
                "match_rate": "84%",
                "tags": ["Event-Driven", "Kafka", "PostgreSQL", "Redis"],
                "apply_url": "https://momo.vn/careers"
            }
        ]

        cards = []
        for i, j in enumerate(sample_jobs, 1):
            cards.append(
                f"#### {i}. {j['title']} — **{j['company']}**\n"
                f"- **Địa điểm:** {j['location']} | **Mức lương:** {j['salary']}\n"
                f"- **Độ phù hợp:** `{j['match_rate']}` | **Tags:** {', '.join(j['tags'])}\n"
                f"- [Xem chi tiết & Ứng tuyển]({j['apply_url']})"
            )

        markdown_body = (
            f"### Danh Sách Việc Làm Phù Hợp Cho '{query}'\n\n"
            + "\n\n".join(cards)
            + "\n\n*(Hiển thị dữ liệu mẫu đối tác. Cấu hình TAVILY_API_KEY trong file .env để tìm kiếm trực tiếp thời gian thực)*"
        )

        return markdown_body, {
            "source": "fallback_curated",
            "jobs": sample_jobs,
            "items": sample_jobs,
            "total_found": len(sample_jobs)
        }
