"""Fixed interpreter. Only this trusted code executes; model output is data."""
import asyncio
import base64
import json
import os
import sys
import time
from urllib.parse import parse_qs, urlsplit

from playwright.async_api import async_playwright

from guard.contracts import SandboxSpec, WRITE, check_step, check_workflow, same_origin, validate_inputs


async def execute(spec: SandboxSpec, origin: str, executable: str | None = None) -> dict:
    check_workflow(spec.workflow, spec.operation, spec.approved)
    validate_inputs(spec.inputs, spec.operation)
    started = time.monotonic()
    result = {"status": "OBSERVED", "trace": [], "fields": {}, "targets": [], "text": "", "screenshots": []}
    if spec.mode == "containment":
        # A fixed, harmless workload, never model code. Supervisor must kill it.
        while True:
            await asyncio.sleep(1)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, chromium_sandbox=True, executable_path=executable)
        context = await browser.new_context(viewport={"width": 1280, "height": 900},
                                           accept_downloads=False, service_workers="block")
        page = await context.new_page()
        page.set_default_timeout(5000)

        async def route_handler(route):
            req = route.request
            allowed = same_origin(req.url, origin)
            path = urlsplit(req.url).path
            if req.method not in {"GET", "POST"} or path not in {"/", "/requests", "/favicon.ico"}:
                allowed = False
            if req.method == "POST":
                form = parse_qs(req.post_data or "", keep_blank_values=True)
                expected = {k: [v] for k, v in spec.inputs.items()}
                allowed = allowed and spec.operation == WRITE and spec.approved and path == "/requests" and form == expected
            if not allowed:
                result["trace"].append({"kind": "POLICY_BLOCK", "reason": "NETWORK_OR_WRITE_DENIED"})
                await route.abort("blockedbyclient")
            else:
                await route.continue_()

        await context.route("**/*", route_handler)
        await context.route_web_socket("**/*", lambda ws: ws.close())
        try:
            await page.goto(origin, wait_until="domcontentloaded", timeout=10000)
            for step in spec.workflow.steps:
                check_step(step, spec.operation, spec.approved)
                begin = time.monotonic()
                target = page.locator(f'[data-target="{step.target}"]') if step.target else None
                if step.action == "navigate":
                    await page.goto(origin + "/", wait_until="domcontentloaded")
                elif step.action == "fill":
                    await target.fill(spec.inputs[step.value_from])
                elif step.action == "click":
                    await target.click()
                    await page.wait_for_load_state("domcontentloaded")
                elif step.action == "wait_for":
                    await target.wait_for(state="visible")
                elif step.action == "read":
                    # Unknown order is a valid branch of the reusable read workflow.
                    if await page.locator('[data-target="not_found"]').count():
                        result["not_found"] = True
                    else:
                        await target.wait_for(state="visible")
                        fields = target.locator("[data-field]")
                        for i in range(min(await fields.count(), 20)):
                            item = fields.nth(i)
                            result["fields"][await item.get_attribute("data-field")] = (await item.inner_text())[:1200]
                result["trace"].append({"kind": "BROWSER_ACTION", "step": step.model_dump(),
                                        "duration_ms": round((time.monotonic() - begin) * 1000)})
            result["targets"] = await page.locator("[data-target]").evaluate_all(
                "els => els.slice(0,30).map(e => ({target:e.dataset.target, tag:e.tagName, text:(e.innerText || e.getAttribute('placeholder') || '').slice(0,150)}))")
            # Fixed source code only; never a model-controlled evaluate string.
            result["text"] = (await page.locator("body").inner_text())[:8000]
        except Exception as exc:
            result["status"] = "PORTAL_CHANGED"
            result["error"] = str(exc)[:1200]
        finally:
            try:
                shot = await page.screenshot(full_page=False, timeout=4000)
                result["screenshots"] = [base64.b64encode(shot).decode()]
            except Exception:
                result["screenshots"] = []
            await browser.close()
    result["duration_ms"] = round((time.monotonic() - started) * 1000)
    return result


if __name__ == "__main__":
    raw = os.environ.pop("SKG_JOB_JSON", "") or sys.stdin.read(65537)
    if len(raw.encode()) > 65536:
        raise ValueError("Job payload exceeds 64 KiB")
    value = SandboxSpec.model_validate_json(raw)
    output = asyncio.run(execute(value, os.environ["PORTAL_BASE_URL"]))
    sys.stdout.write(json.dumps(output))
