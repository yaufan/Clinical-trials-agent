"""End-to-end smoke test against a running stack.

    python scripts/smoke_test.py --base-url http://localhost:8000 [--timeout 1800]

Creates a project from the built-in example, starts a run, waits for the evidence gate,
auto-confirms every evidence item, waits for completion and downloads the Markdown export.
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://localhost:8000")
    ap.add_argument("--timeout", type=float, default=1800.0, help="seconds to wait for each half of the pipeline")
    ap.add_argument("--out", default="smoke-protocol.md")
    args = ap.parse_args()
    api = args.base_url.rstrip("/") + "/api"
    c = httpx.Client(timeout=60.0)

    health = c.get(f"{api}/health").json()
    print("health:", health)
    mcp = c.get(f"{api}/meta/mcp-health").json()
    for name, st in mcp.items():
        print(f"  mcp {name}: {'OK' if st.get('ok') else 'DOWN — ' + str(st.get('error'))}")

    example = c.get(f"{api}/meta/example").json()
    project = c.post(f"{api}/projects", json={"name": "Smoke test", "input": example}).json()
    run = c.post(f"{api}/projects/{project['id']}/runs").json()
    rid = run["run_id"]
    print("run:", rid)

    def wait_for(stages: set[str], limit: float) -> dict:
        t0 = time.time()
        last = None
        while time.time() - t0 < limit:
            st = c.get(f"{api}/runs/{rid}").json()
            if st["stage"] != last:
                print(f"  [{time.time() - t0:6.0f}s] stage = {st['stage']}  llm_calls={st['llm_calls']} tool_calls={st['tool_calls']}")
                last = st["stage"]
            if st["stage"] in stages:
                return st
            time.sleep(5)
        raise SystemExit(f"timed out waiting for {stages}")

    st = wait_for({"awaiting_evidence_confirmation", "failed"}, args.timeout)
    if st["stage"] == "failed":
        print("FAILED:", st["error"])
        return 1
    print(f"evidence items: {len(st['evidence']['items'])}; benchmark rows: {len(st['evidence']['benchmark_rows'])}")
    c.post(f"{api}/runs/{rid}/confirm-evidence", json={"reviewer_notes": "auto-confirmed by smoke test"}).raise_for_status()
    st = wait_for({"completed", "failed"}, args.timeout)
    if st["stage"] == "failed":
        print("FAILED:", st["error"])
        return 1
    audit = st["audits"][-1]
    print(f"sections: {len(st['sections'])}; audit: pass={audit['n_pass']} partial={audit['n_partial']} fail={audit['n_fail']} verdict={audit['overall_verdict']}")
    md = c.get(f"{api}/runs/{rid}/export.md").text
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(md)
    print(f"wrote {args.out} ({len(md)} chars); warnings: {len(st['warnings'])}")
    for w in st["warnings"][:10]:
        print("  warn:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
