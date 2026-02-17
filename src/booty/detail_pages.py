"""Detail pages for check/status links with realtime progress.

Provides FastAPI routes for job-specific detail pages that show realtime
progress via Server-Sent Events (SSE). These pages are linked from GitHub
check runs and commit statuses to give users visibility into what Booty is
doing in realtime.

Routes:
- /detail/verifier/{job_id} - Verifier job detail with live test output
- /detail/main/{delivery_id} - Main verification flow (Governor + Verifier)
- /detail/governor/{delivery_id} - Governor decision flow
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Dict, Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# In-memory job state tracking (in production, use Redis or similar)
_job_states: Dict[str, Dict[str, Any]] = {}
_delivery_states: Dict[str, Dict[str, Any]] = {}


# Mock Redis client for test compatibility
class MockRedisClient:
    """Mock Redis client that uses in-memory storage."""
    
    def get(self, key: str) -> Optional[bytes]:
        """Get value from in-memory storage."""
        # Extract job type and ID from Redis key format
        # Expected format: "booty:detail:{job_type}:{job_id}"
        parts = key.split(":")
        if len(parts) >= 4:
            job_type = parts[2]
            job_id = ":".join(parts[3:])  # Handle IDs with colons
            
            if job_type == "verifier":
                state = _job_states.get(job_id)
            elif job_type in ("main-verify", "main"):
                state = _delivery_states.get(job_id)
            elif job_type == "governor":
                state = _delivery_states.get(job_id)
            else:
                return None
            
            if state:
                return json.dumps(state).encode()
        return None


redis_client = MockRedisClient()


def register_job_state(job_id: str, state: Dict[str, Any]) -> None:
    """Register or update job state for detail page access."""
    _job_states[job_id] = {
        **state,
        "last_updated": datetime.utcnow().isoformat(),
    }


def register_delivery_state(delivery_id: str, state: Dict[str, Any]) -> None:
    """Register or update delivery state for main verification detail page."""
    _delivery_states[delivery_id] = {
        **state,
        "last_updated": datetime.utcnow().isoformat(),
    }


def get_job_state(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve current job state."""
    return _job_states.get(job_id)


def get_delivery_state(delivery_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve current delivery state."""
    return _delivery_states.get(delivery_id)


async def get_job_status(job_type: str, job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve job status from storage.
    
    Args:
        job_type: Type of job ("verifier", "main-verify", "governor")
        job_id: Job identifier
        
    Returns:
        Job status dict or None if not found
    """
    try:
        key = f"booty:detail:{job_type}:{job_id}"
        data = redis_client.get(key)
        if data:
            return json.loads(data.decode())
        return None
    except (json.JSONDecodeError, AttributeError):
        return None


async def stream_job_events(job_type: str, job_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """Generate stream of job status updates.
    
    Args:
        job_type: Type of job ("verifier", "main-verify", "governor")
        job_id: Job identifier
        
    Yields:
        Job status update dicts
    """
    max_iterations = 600  # 10 minutes at 1 second intervals
    iteration = 0
    
    while iteration < max_iterations:
        status = await get_job_status(job_type, job_id)
        
        if status is None:
            yield {
                "type": "error",
                "status": "not_found",
                "message": f"Job {job_id} not found",
            }
            break
        
        # Send current status
        yield {
            "type": "update",
            **status,
        }
        
        # Check if job is complete
        job_status = status.get("status", "")
        if job_status in ("completed", "failed", "cancelled"):
            yield {
                "type": "complete",
                **status,
            }
            break
        
        await asyncio.sleep(1)
        iteration += 1
    
    # Timeout fallback
    if iteration >= max_iterations:
        yield {
            "type": "timeout",
            "message": "Stream timeout reached",
        }


def construct_detail_url(job_type: str, job_id: str, base_url: Optional[str] = None) -> Optional[str]:
    """Construct detail page URL.
    
    Args:
        job_type: Type of job ("verifier", "main-verify", "governor")
        job_id: Job identifier
        base_url: Base URL for Booty instance (e.g. https://booty.example.com)
        
    Returns:
        Full detail page URL or None if base_url not provided
    """
    if not base_url or base_url.strip() == "":
        return None
    
    base = base_url.rstrip("/")
    return f"{base}/detail/{job_type}/{job_id}"


async def verifier_event_stream(job_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for verifier job progress.
    
    Yields JSON events with job status, test output, and completion state.
    """
    async for event in stream_job_events("verifier", job_id):
        yield json.dumps(event)


async def main_verification_event_stream(delivery_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for main verification flow (Governor + Verifier).
    
    Yields JSON events with clone status, test progress, Governor decision, etc.
    """
    async for event in stream_job_events("main-verify", delivery_id):
        yield json.dumps(event)


async def governor_event_stream(delivery_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE stream for governor decision flow.
    
    Yields JSON events with decision status and reasoning.
    """
    async for event in stream_job_events("governor", delivery_id):
        yield json.dumps(event)


@router.get("/detail/verifier/{job_id}", response_class=HTMLResponse)
async def verifier_detail_page(job_id: str, request: Request) -> HTMLResponse:
    """Detail page for Verifier job with realtime test output.
    
    Shows live streaming test output while the Verifier is running tests.
    """
    state = get_job_state(job_id)
    
    if state is None:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Verifier Job Not Found</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 40px; }}
                    .error {{ color: #d73a49; }}
                </style>
            </head>
            <body>
                <h1>Verifier Job Not Found</h1>
                <p class="error">Job ID: {job_id}</p>
                <p>This job may not have started yet, or the ID is invalid.</p>
            </body>
            </html>
            """,
            status_code=404,
        )
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Verifier Job Details</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f6f8fa;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 20px;
            }}
            h1 {{
                margin-top: 0;
                color: #24292f;
            }}
            .status {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 600;
            }}
            .status.running {{ background-color: #ddf4ff; color: #0969da; }}
            .status.completed {{ background-color: #dafbe1; color: #1a7f37; }}
            .status.failed {{ background-color: #ffebe9; color: #d1242f; }}
            .output {{
                background-color: #24292f;
                color: #c9d1d9;
                padding: 16px;
                border-radius: 6px;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 12px;
                line-height: 1.5;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                max-height: 600px;
                overflow-y: auto;
            }}
            .meta {{
                color: #57606a;
                font-size: 14px;
                margin-bottom: 16px;
            }}
            .loading {{
                color: #0969da;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Verifier Job Details</h1>
            <div class="meta">
                Job ID: <code>{job_id}</code><br>
                Status: <span class="status" id="status">{state.get("status", "unknown")}</span><br>
                Last Updated: <span id="last-updated">{state.get("last_updated", "N/A")}</span>
            </div>
            <h2>Test Output</h2>
            <div class="output" id="output">{state.get("output", "Waiting for output...")}</div>
            <p class="loading" id="loading">Connecting to live stream...</p>
        </div>
        <script>
            const eventSource = new EventSource('/detail/verifier/{job_id}/stream');
            const outputEl = document.getElementById('output');
            const statusEl = document.getElementById('status');
            const lastUpdatedEl = document.getElementById('last-updated');
            const loadingEl = document.getElementById('loading');
            
            eventSource.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'update') {{
                    outputEl.textContent = data.output || 'No output yet...';
                    statusEl.textContent = data.status;
                    statusEl.className = 'status ' + data.status;
                    lastUpdatedEl.textContent = data.last_updated;
                    loadingEl.textContent = 'Live updates active';
                    loadingEl.style.color = '#1a7f37';
                }} else if (data.type === 'complete') {{
                    outputEl.textContent = data.final_output || data.output || 'Completed';
                    statusEl.textContent = data.conclusion || 'completed';
                    statusEl.className = 'status completed';
                    loadingEl.textContent = 'Job completed';
                    loadingEl.style.color = '#1a7f37';
                    eventSource.close();
                }} else if (data.type === 'error') {{
                    loadingEl.textContent = 'Error: ' + data.message;
                    loadingEl.style.color = '#d1242f';
                    eventSource.close();
                }} else if (data.type === 'timeout') {{
                    loadingEl.textContent = 'Stream timeout - refresh to reconnect';
                    loadingEl.style.color = '#9a6700';
                    eventSource.close();
                }}
            }};
            
            eventSource.onerror = function(err) {{
                console.error('EventSource error:', err);
                loadingEl.textContent = 'Connection error - refresh to retry';
                loadingEl.style.color = '#d1242f';
                eventSource.close();
            }};
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/detail/verifier/{job_id}/stream")
async def verifier_stream(job_id: str) -> EventSourceResponse:
    """SSE endpoint for verifier job realtime updates."""
    return EventSourceResponse(verifier_event_stream(job_id))


@router.get("/detail/main-verify/{delivery_id}", response_class=HTMLResponse)
async def main_verification_detail_page(delivery_id: str, request: Request) -> HTMLResponse:
    """Detail page for main verification flow (Governor + Verifier on main).
    
    Shows realtime progress: clone → tests → Governor evaluate → HOLD/ALLOW.
    """
    state = get_delivery_state(delivery_id)
    
    if state is None:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Main Verification Not Found</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 40px; }}
                    .error {{ color: #d73a49; }}
                </style>
            </head>
            <body>
                <h1>Main Verification Not Found</h1>
                <p class="error">Delivery ID: {delivery_id}</p>
                <p>This verification may not have started yet, or the ID is invalid.</p>
            </body>
            </html>
            """,
            status_code=404,
        )
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Main Verification</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f6f8fa;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 20px;
            }}
            h1 {{
                margin-top: 0;
                color: #24292f;
            }}
            .phase {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 600;
                background-color: #ddf4ff;
                color: #0969da;
            }}
            .decision {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 14px;
                font-weight: 600;
            }}
            .decision.ALLOW {{ background-color: #dafbe1; color: #1a7f37; }}
            .decision.HOLD {{ background-color: #fff8c5; color: #9a6700; }}
            .output {{
                background-color: #24292f;
                color: #c9d1d9;
                padding: 16px;
                border-radius: 6px;
                font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                font-size: 12px;
                line-height: 1.5;
                overflow-x: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                max-height: 600px;
                overflow-y: auto;
            }}
            .meta {{
                color: #57606a;
                font-size: 14px;
                margin-bottom: 16px;
            }}
            .loading {{
                color: #0969da;
                font-style: italic;
            }}
            .timeline {{
                margin: 20px 0;
                padding-left: 20px;
                border-left: 2px solid #d0d7de;
            }}
            .timeline-item {{
                margin-bottom: 12px;
                padding-left: 12px;
            }}
            .timeline-item.active {{
                font-weight: 600;
                color: #0969da;
            }}
            .timeline-item.complete {{
                color: #1a7f37;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Main Verification</h1>
            <div class="meta">
                Delivery ID: <code>{delivery_id}</code><br>
                Phase: <span class="phase" id="phase">{state.get("phase", "unknown")}</span><br>
                Governor Decision: <span class="decision" id="decision">{state.get("governor_decision", "pending")}</span><br>
                Last Updated: <span id="last-updated">{state.get("last_updated", "N/A")}</span>
            </div>
            
            <h2>Progress</h2>
            <div class="timeline" id="timeline">
                <div class="timeline-item" id="phase-clone">📦 Clone repository</div>
                <div class="timeline-item" id="phase-test">🧪 Run tests (Verifier)</div>
                <div class="timeline-item" id="phase-evaluate">⚖️ Evaluate (Governor)</div>
                <div class="timeline-item" id="phase-complete">✅ Complete</div>
            </div>
            
            <h2>Output</h2>
            <div class="output" id="output">{state.get("output", "Waiting for output...")}</div>
            <p class="loading" id="loading">Connecting to live stream...</p>
        </div>
        <script>
            const eventSource = new EventSource('/detail/main-verify/{delivery_id}/stream');
            const outputEl = document.getElementById('output');
            const phaseEl = document.getElementById('phase');
            const decisionEl = document.getElementById('decision');
            const lastUpdatedEl = document.getElementById('last-updated');
            const loadingEl = document.getElementById('loading');
            
            function updateTimeline(currentPhase) {{
                const phases = ['clone', 'test', 'evaluate', 'complete'];
                const currentIndex = phases.indexOf(currentPhase);
                
                phases.forEach((phase, index) => {{
                    const el = document.getElementById('phase-' + phase);
                    if (index < currentIndex) {{
                        el.className = 'timeline-item complete';
                    }} else if (index === currentIndex) {{
                        el.className = 'timeline-item active';
                    }} else {{
                        el.className = 'timeline-item';
                    }}
                }});
            }}
            
            eventSource.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'update') {{
                    outputEl.textContent = data.output || 'No output yet...';
                    phaseEl.textContent = data.phase;
                    
                    if (data.governor_decision) {{
                        decisionEl.textContent = data.governor_decision;
                        decisionEl.className = 'decision ' + data.governor_decision;
                    }}
                    
                    lastUpdatedEl.textContent = data.last_updated;
                    loadingEl.textContent = 'Live updates active';
                    loadingEl.style.color = '#1a7f37';
                    
                    updateTimeline(data.phase);
                }} else if (data.type === 'complete') {{
                    outputEl.textContent = data.final_output || data.output || 'Completed';
                    phaseEl.textContent = 'complete';
                    
                    if (data.governor_decision) {{
                        decisionEl.textContent = data.governor_decision;
                        decisionEl.className = 'decision ' + data.governor_decision;
                    }}
                    
                    loadingEl.textContent = 'Verification completed';
                    loadingEl.style.color = '#1a7f37';
                    updateTimeline('complete');
                    eventSource.close();
                }} else if (data.type === 'error') {{
                    loadingEl.textContent = 'Error: ' + data.message;
                    loadingEl.style.color = '#d1242f';
                    eventSource.close();
                }} else if (data.type === 'timeout') {{
                    loadingEl.textContent = 'Stream timeout - refresh to reconnect';
                    loadingEl.style.color = '#9a6700';
                    eventSource.close();
                }}
            }};
            
            eventSource.onerror = function(err) {{
                console.error('EventSource error:', err);
                loadingEl.textContent = 'Connection error - refresh to retry';
                loadingEl.style.color = '#d1242f';
                eventSource.close();
            }};
            
            // Initialize timeline
            updateTimeline('{state.get("phase", "unknown")}');
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/detail/main-verify/{delivery_id}/stream")
async def main_verification_stream(delivery_id: str) -> EventSourceResponse:
    """SSE endpoint for main verification flow realtime updates."""
    return EventSourceResponse(main_verification_event_stream(delivery_id))


@router.get("/detail/main/{delivery_id}", response_class=HTMLResponse)
async def main_detail_page_alias(delivery_id: str, request: Request) -> HTMLResponse:
    """Alias for main verification detail page (backward compatibility)."""
    return await main_verification_detail_page(delivery_id, request)


@router.get("/detail/main/{delivery_id}/stream")
async def main_stream_alias(delivery_id: str) -> EventSourceResponse:
    """Alias for main verification stream (backward compatibility)."""
    return EventSourceResponse(main_verification_event_stream(delivery_id))


@router.get("/detail/governor/{delivery_id}", response_class=HTMLResponse)
async def governor_detail_page(delivery_id: str, request: Request) -> HTMLResponse:
    """Detail page for Release Governor decision flow.
    
    Shows governor evaluation and decision (HOLD/ALLOW).
    """
    state = get_delivery_state(delivery_id)
    
    if state is None:
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Governor Decision Not Found</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; margin: 40px; }}
                    .error {{ color: #d73a49; }}
                </style>
            </head>
            <body>
                <h1>Governor Decision Not Found</h1>
                <p class="error">Delivery ID: {delivery_id}</p>
                <p>This decision may not have started yet, or the ID is invalid.</p>
            </body>
            </html>
            """,
            status_code=404,
        )
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Release Governor</title>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f6f8fa;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 20px;
            }}
            h1 {{
                margin-top: 0;
                color: #24292f;
            }}
            .decision {{
                display: inline-block;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 18px;
                font-weight: 600;
                margin: 16px 0;
            }}
            .decision.ALLOW {{ background-color: #dafbe1; color: #1a7f37; }}
            .decision.HOLD {{ background-color: #fff8c5; color: #9a6700; }}
            .decision.evaluating {{ background-color: #ddf4ff; color: #0969da; }}
            .checks {{
                background-color: #f6f8fa;
                padding: 16px;
                border-radius: 6px;
                margin: 16px 0;
            }}
            .check-item {{
                padding: 8px 0;
                border-bottom: 1px solid #d0d7de;
            }}
            .check-item:last-child {{
                border-bottom: none;
            }}
            .meta {{
                color: #57606a;
                font-size: 14px;
                margin-bottom: 16px;
            }}
            .loading {{
                color: #0969da;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚖️ Release Governor</h1>
            <div class="meta">
                Delivery ID: <code>{delivery_id}</code><br>
                Last Updated: <span id="last-updated">{state.get("last_updated", "N/A")}</span>
            </div>
            
            <h2>Decision</h2>
            <div class="decision" id="decision">{state.get("decision", "evaluating")}</div>
            
            <h2>Checks</h2>
            <div class="checks" id="checks">
                <div class="check-item">Loading checks...</div>
            </div>
            
            <p class="loading" id="loading">Connecting to live stream...</p>
        </div>
        <script>
            const eventSource = new EventSource('/detail/governor/{delivery_id}/stream');
            const decisionEl = document.getElementById('decision');
            const checksEl = document.getElementById('checks');
            const lastUpdatedEl = document.getElementById('last-updated');
            const loadingEl = document.getElementById('loading');
            
            eventSource.onmessage = function(event) {{
                const data = JSON.parse(event.data);
                
                if (data.type === 'update') {{
                    if (data.decision) {{
                        decisionEl.textContent = data.decision;
                        decisionEl.className = 'decision ' + data.decision;
                    }}
                    
                    if (data.checks && Array.isArray(data.checks)) {{
                        checksEl.innerHTML = data.checks.map(check => 
                            `<div class="check-item">${{check}}</div>`
                        ).join('');
                    }}
                    
                    lastUpdatedEl.textContent = data.last_updated;
                    loadingEl.textContent = 'Live updates active';
                    loadingEl.style.color = '#1a7f37';
                }} else if (data.type === 'complete') {{
                    if (data.decision) {{
                        decisionEl.textContent = data.decision;
                        decisionEl.className = 'decision ' + data.decision;
                    }}
                    
                    loadingEl.textContent = 'Decision completed';
                    loadingEl.style.color = '#1a7f37';
                    eventSource.close();
                }} else if (data.type === 'error') {{
                    loadingEl.textContent = 'Error: ' + data.message;
                    loadingEl.style.color = '#d1242f';
                    eventSource.close();
                }} else if (data.type === 'timeout') {{
                    loadingEl.textContent = 'Stream timeout - refresh to reconnect';
                    loadingEl.style.color = '#9a6700';
                    eventSource.close();
                }}
            }};
            
            eventSource.onerror = function(err) {{
                console.error('EventSource error:', err);
                loadingEl.textContent = 'Connection error - refresh to retry';
                loadingEl.style.color = '#d1242f';
                eventSource.close();
            }};
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/detail/governor/{delivery_id}/stream")
async def governor_stream(delivery_id: str) -> EventSourceResponse:
    """SSE endpoint for governor decision flow realtime updates."""
    return EventSourceResponse(governor_event_stream(delivery_id))
