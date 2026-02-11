"""
Streaming utilities for async generators and SSE.
"""

import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator, TypeVar, Generic, Any, Optional, Callable
from datetime import datetime
import json

T = TypeVar("T")


@dataclass
class StreamBuffer(Generic[T]):
    """
    Buffer for streaming data with backpressure support.
    
    Usage:
        buffer = StreamBuffer[str]()
        
        # Producer
        await buffer.put("Hello")
        await buffer.put("World")
        await buffer.close()
        
        # Consumer
        async for item in buffer:
            print(item)
    """
    
    max_size: int = 100
    _queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    _closed: bool = False
    _error: Optional[Exception] = None
    
    def __post_init__(self):
        self._queue = asyncio.Queue(maxsize=self.max_size)
    
    async def put(self, item: T) -> None:
        """Add an item to the buffer."""
        if self._closed:
            raise RuntimeError("Buffer is closed")
        await self._queue.put(item)
    
    def put_nowait(self, item: T) -> None:
        """Add an item without waiting (may raise QueueFull)."""
        if self._closed:
            raise RuntimeError("Buffer is closed")
        self._queue.put_nowait(item)
    
    async def close(self, error: Optional[Exception] = None) -> None:
        """Close the buffer, optionally with an error."""
        self._closed = True
        self._error = error
        await self._queue.put(None)  # Sentinel value
    
    async def __aiter__(self) -> AsyncGenerator[T, None]:
        """Iterate over items in the buffer."""
        while True:
            item = await self._queue.get()
            if item is None:  # Sentinel
                if self._error:
                    raise self._error
                break
            yield item


@dataclass
class SSEEvent:
    """Server-Sent Event data structure."""
    
    event: str
    data: Any
    id: Optional[str] = None
    retry: Optional[int] = None
    
    def encode(self) -> str:
        """Encode the event as an SSE string."""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        lines.append(f"event: {self.event}")
        
        # Encode data as JSON if not a string
        if isinstance(self.data, str):
            data_str = self.data
        else:
            data_str = json.dumps(self.data)
        
        # Handle multi-line data
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")
        
        return "\n".join(lines) + "\n\n"


class SSEStream:
    """
    Server-Sent Events stream manager.
    
    Usage:
        stream = SSEStream()
        
        async def generate():
            async for event in stream:
                yield event.encode()
        
        # Emit events
        await stream.emit("status", {"message": "Processing..."})
        await stream.emit("token", "Hello")
        await stream.close()
    """
    
    def __init__(self, max_buffer: int = 100):
        self._buffer: StreamBuffer[SSEEvent] = StreamBuffer(max_size=max_buffer)
        self._event_id = 0
    
    async def emit(
        self,
        event: str,
        data: Any,
        include_id: bool = True,
    ) -> None:
        """Emit an event to the stream."""
        self._event_id += 1
        sse_event = SSEEvent(
            event=event,
            data=data,
            id=str(self._event_id) if include_id else None,
        )
        await self._buffer.put(sse_event)
    
    async def emit_status(self, phase: str, message: str) -> None:
        """Emit a status event."""
        await self.emit("status", {"phase": phase, "message": message})
    
    async def emit_token(self, token: str) -> None:
        """Emit a token event."""
        await self.emit("token", token, include_id=False)
    
    async def emit_sources(self, sources: list[dict]) -> None:
        """Emit sources event."""
        await self.emit("sources", sources)
    
    async def emit_error(self, code: str, message: str, recoverable: bool = False) -> None:
        """Emit an error event."""
        await self.emit("error", {
            "code": code,
            "message": message,
            "recoverable": recoverable,
        })
    
    async def emit_done(self, metadata: dict) -> None:
        """Emit completion event and close stream."""
        await self.emit("done", metadata)
        await self.close()
    
    async def close(self, error: Optional[Exception] = None) -> None:
        """Close the stream."""
        await self._buffer.close(error)
    
    async def __aiter__(self) -> AsyncGenerator[SSEEvent, None]:
        """Iterate over events."""
        async for event in self._buffer:
            yield event


async def merge_streams(
    *streams: AsyncGenerator[T, None],
) -> AsyncGenerator[T, None]:
    """
    Merge multiple async generators into a single stream.
    
    Items are yielded in the order they become available.
    """
    queue: asyncio.Queue[tuple[int, T | Exception | None]] = asyncio.Queue()
    active = len(streams)
    
    async def forward(index: int, stream: AsyncGenerator[T, None]):
        nonlocal active
        try:
            async for item in stream:
                await queue.put((index, item))
        except Exception as e:
            await queue.put((index, e))
        finally:
            active -= 1
            await queue.put((index, None))
    
    # Start all forwarders
    tasks = [asyncio.create_task(forward(i, stream)) for i, stream in enumerate(streams)]
    
    try:
        finished = 0
        while finished < len(streams):
            index, item = await queue.get()
            if item is None:
                finished += 1
            elif isinstance(item, Exception):
                raise item
            else:
                yield item
    finally:
        for task in tasks:
            task.cancel()


def throttle_stream(
    stream: AsyncGenerator[T, None],
    min_interval: float = 0.05,
) -> AsyncGenerator[T, None]:
    """
    Throttle a stream to emit at most one item per interval.
    
    Useful for rate-limiting token streams to avoid overwhelming clients.
    """
    async def throttled():
        last_emit = 0.0
        
        async for item in stream:
            now = asyncio.get_event_loop().time()
            elapsed = now - last_emit
            
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
            
            yield item
            last_emit = asyncio.get_event_loop().time()
    
    return throttled()
