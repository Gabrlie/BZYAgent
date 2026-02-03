"""
SSE helpers
"""
import json
from typing import AsyncIterable, AsyncIterator
from fastapi.responses import StreamingResponse


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def sse_event(data: dict) -> str:
    """格式化 SSE 事件"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def sse_response(generator: AsyncIterable[str] | AsyncIterator[str]) -> StreamingResponse:
    """构建标准 SSE 响应"""
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
