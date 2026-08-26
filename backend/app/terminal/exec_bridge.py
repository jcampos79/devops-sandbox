"""Bridges an xterm.js WebSocket session to a Kubernetes `exec` stream on
the sandbox pod (spec Section 17). Kept intentionally small: read from the
browser, write to the pod's stdin; read from the pod's stdout/stderr,
write to the browser. No SSH server inside the container, no direct
Kubernetes API exposure to the browser -- the browser only ever talks to
this WebSocket endpoint.
"""

import asyncio
import logging

from fastapi import WebSocket, WebSocketDisconnect
from kubernetes import stream
from kubernetes.client.rest import ApiException

from app.kubernetes.client import k8s

logger = logging.getLogger("sandbox_platform")


async def bridge_terminal(websocket: WebSocket, namespace: str, pod_name: str, shell: str) -> None:
    """Runs until the browser disconnects or the pod's exec session ends.
    Never logs command input/output (spec Section 36)."""
    try:
        exec_stream = stream.stream(
            k8s.core_v1.connect_get_namespaced_pod_exec,
            pod_name,
            namespace,
            command=[shell],
            stderr=True,
            stdin=True,
            stdout=True,
            tty=True,
            _preload_content=False,
        )
    except ApiException as e:
        logger.error("Failed to open exec stream for pod=%s/%s: %s", namespace, pod_name, e)
        await websocket.close(code=1011, reason="Failed to attach to sandbox")
        return

    async def pump_pod_to_browser() -> None:
        while exec_stream.is_open():
            exec_stream.update(timeout=1)
            if exec_stream.peek_stdout():
                await websocket.send_text(exec_stream.read_stdout())
            if exec_stream.peek_stderr():
                await websocket.send_text(exec_stream.read_stderr())
            await asyncio.sleep(0.01)

    async def pump_browser_to_pod() -> None:
        try:
            while True:
                data = await websocket.receive_text()
                exec_stream.write_stdin(data)
        except WebSocketDisconnect:
            pass

    pod_to_browser = asyncio.create_task(pump_pod_to_browser())
    browser_to_pod = asyncio.create_task(pump_browser_to_pod())

    done, pending = await asyncio.wait(
        {pod_to_browser, browser_to_pod}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()
    exec_stream.close()
