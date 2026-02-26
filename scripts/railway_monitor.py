#!/usr/bin/env python3
"""
Railway Deployment Monitor — Automated error scanner for Masaad Estimator
Polls Railway GraphQL API for build/deploy status and surfaces errors.

Usage:
    python scripts/railway_monitor.py              # One-shot scan
    python scripts/railway_monitor.py --watch      # Continuous monitoring (30s interval)
    python scripts/railway_monitor.py --watch 10   # Continuous monitoring (10s interval)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

import requests

# Force UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ── Configuration ──────────────────────────────────────────────────────
RAILWAY_API = "https://backboard.railway.app/graphql/v2"
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN", "")
WORKSPACE_ID = os.getenv("RAILWAY_WORKSPACE_ID", "bf910a79-c1d7-4875-b04e-31e8ab76f3f0")
PROJECT_NAME = os.getenv("RAILWAY_PROJECT_NAME", "soothing-motivation")

# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


if not RAILWAY_TOKEN:
    print(
        f"{RED}ERROR: RAILWAY_TOKEN environment variable is not set.\n"
        f"Export it before running this script:\n"
        f"  export RAILWAY_TOKEN=<your-railway-api-token>\n"
        f"Obtain a token at: https://railway.app/account/tokens{RESET}",
        file=sys.stderr,
    )
    sys.exit(1)

_session = requests.Session()
_session.headers.update({
    "Authorization": f"Bearer {RAILWAY_TOKEN}",
    "Content-Type": "application/json",
})


def gql(query: str, variables: dict = None) -> dict:
    """Execute a GraphQL query against Railway API."""
    try:
        resp = _session.post(
            RAILWAY_API,
            json={"query": query, "variables": variables or {}},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        return {"errors": [{"message": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}]}
    except Exception as e:
        return {"errors": [{"message": str(e)}]}


def get_deployments():
    """Fetch recent deployments via workspace projects query (works with team tokens)."""
    query = """
    query($workspaceId: String!) {
      projects(workspaceId: $workspaceId) {
        edges {
          node {
            id
            name
            services {
              edges {
                node {
                  id
                  name
                  deployments(first: 3) {
                    edges {
                      node {
                        id
                        status
                        createdAt
                        updatedAt
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    return gql(query, {"workspaceId": WORKSPACE_ID})


def get_build_logs(deployment_id: str):
    """Fetch build logs for a deployment."""
    query = """
    query($deploymentId: String!) {
      buildLogs(deploymentId: $deploymentId, limit: 100) {
        message
        severity
        timestamp
      }
    }
    """
    return gql(query, {"deploymentId": deployment_id})


def get_deploy_logs(deployment_id: str):
    """Fetch runtime deploy logs for a deployment."""
    query = """
    query($deploymentId: String!) {
      deploymentLogs(deploymentId: $deploymentId, limit: 50) {
        message
        severity
        timestamp
      }
    }
    """
    return gql(query, {"deploymentId": deployment_id})


def status_color(status: str) -> str:
    """Return colored status string."""
    s = status.upper() if status else "UNKNOWN"
    if s in ("SUCCESS", "READY", "RUNNING"):
        return f"{GREEN}{s}{RESET}"
    elif s in ("BUILDING", "DEPLOYING", "INITIALIZING", "WAITING"):
        return f"{YELLOW}{s}{RESET}"
    elif s in ("FAILED", "CRASHED", "ERROR", "REMOVED"):
        return f"{RED}{s}{RESET}"
    return f"{CYAN}{s}{RESET}"


def format_time(iso_str: str) -> str:
    """Format ISO timestamp to human-readable."""
    if not iso_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        mins = int(delta.total_seconds() / 60)
        if mins < 1:
            return "just now"
        elif mins < 60:
            return f"{mins}m ago"
        elif mins < 1440:
            return f"{mins // 60}h {mins % 60}m ago"
        return f"{mins // 1440}d ago"
    except Exception:
        return iso_str[:19]


def scan_logs_for_errors(logs: list) -> list:
    """Extract error lines from log entries."""
    errors = []
    error_keywords = [
        "error", "Error", "ERROR", "failed", "FAILED", "fatal",
        "FATAL", "exception", "Exception", "traceback", "Traceback",
        "ModuleNotFoundError", "ImportError", "SyntaxError",
        "TypeError", "ValueError", "KeyError", "AttributeError",
        "cannot find", "not found", "permission denied", "ENOENT",
        "npm ERR!", "exit code 1", "killed", "OOMKilled",
    ]
    for log in (logs or []):
        msg = log.get("message", "")
        severity = log.get("severity", "").upper()
        if severity in ("ERROR", "FATAL") or any(kw in msg for kw in error_keywords):
            errors.append(msg.strip())
    return errors


def print_separator():
    print(f"{DIM}{'-' * 70}{RESET}")


def run_scan():
    """Execute one full scan of all services."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{BOLD}{CYAN}+{'=' * 62}+{RESET}")
    print(f"{BOLD}{CYAN}|  RAILWAY DEPLOYMENT MONITOR -- Masaad Estimator              |{RESET}")
    print(f"{BOLD}{CYAN}|  Scan: {now}                              |{RESET}")
    print(f"{BOLD}{CYAN}+{'=' * 62}+{RESET}")

    result = get_deployments()

    if "errors" in result:
        print(f"\n{RED}API Error: {result['errors'][0]['message'][:100]}{RESET}")
        return

    projects = result.get("data", {}).get("projects", {}).get("edges", [])
    if not projects:
        print(f"\n{YELLOW}No projects found in workspace{RESET}")
        return

    all_healthy = True

    for proj_edge in projects:
        proj = proj_edge["node"]
        proj_name = proj["name"]
        print(f"\n{BOLD}{CYAN}Project: {proj_name}{RESET}")

        services = proj.get("services", {}).get("edges", [])
        for svc_edge in services:
            svc = svc_edge["node"]
            svc_name = svc["name"]
            svc_id = svc["id"]
            deployments = svc.get("deployments", {}).get("edges", [])

            print(f"\n  {BOLD}Service: {svc_name}{RESET} ({svc_id[:8]}...)")
            print_separator()

            if not deployments:
                print(f"    {DIM}No deployments found{RESET}")
                continue

            for dep_edge in deployments:
                dep = dep_edge["node"]
                dep_id = dep["id"]
                status = dep.get("status", "UNKNOWN")
                created = format_time(dep.get("createdAt"))
                updated = format_time(dep.get("updatedAt"))

                print(f"    Deploy: {dep_id[:12]}...  Status: {status_color(status)}  ({created})")

                # Check for errors in failed/crashed deployments
                if status.upper() in ("FAILED", "CRASHED", "ERROR"):
                    all_healthy = False
                    # Get build logs
                    blog = get_build_logs(dep_id)
                    build_logs = blog.get("data", {}).get("buildLogs", [])
                    errors = scan_logs_for_errors(build_logs)
                    if errors:
                        print(f"    {RED}BUILD ERRORS ({len(errors)}):{RESET}")
                        for e in errors[-8:]:
                            print(f"      {RED}x{RESET} {e[:120]}")

                    # Get deploy logs
                    dlog = get_deploy_logs(dep_id)
                    deploy_logs = dlog.get("data", {}).get("deploymentLogs", [])
                    errors = scan_logs_for_errors(deploy_logs)
                    if errors:
                        print(f"    {RED}DEPLOY ERRORS ({len(errors)}):{RESET}")
                        for e in errors[-8:]:
                            print(f"      {RED}x{RESET} {e[:120]}")

                elif status.upper() in ("BUILDING", "DEPLOYING", "INITIALIZING"):
                    print(f"    {YELLOW}~ In progress...{RESET}")
                    # Show recent build logs for in-progress builds
                    blog = get_build_logs(dep_id)
                    build_logs = blog.get("data", {}).get("buildLogs", [])
                    if build_logs:
                        last_lines = build_logs[-3:]
                        for line in last_lines:
                            msg = line.get("message", "").strip()
                            if msg:
                                print(f"      {DIM}{msg[:100]}{RESET}")

                elif status.upper() == "SUCCESS":
                    # For latest successful deploy, show last few runtime lines
                    if dep_edge == deployments[0]:  # only for latest
                        dlog = get_deploy_logs(dep_id)
                        deploy_logs = dlog.get("data", {}).get("deploymentLogs", [])
                        warnings = [
                            l.get("message", "").strip()
                            for l in (deploy_logs or [])
                            if l.get("severity", "").upper() == "ERROR"
                            or "error" in l.get("message", "").lower()
                            or "warning" in l.get("message", "").lower()
                        ]
                        if warnings:
                            print(f"    {YELLOW}WARNINGS ({len(warnings)}):{RESET}")
                            for w in warnings[-5:]:
                                print(f"      {YELLOW}!{RESET} {w[:120]}")

    if all_healthy:
        print(f"\n{GREEN}{BOLD}[OK] All services healthy{RESET}\n")
    else:
        print(f"\n{RED}{BOLD}[FAIL] Issues detected -- see errors above{RESET}\n")


def main():
    watch = "--watch" in sys.argv
    interval = 30

    # Parse optional interval
    if watch:
        idx = sys.argv.index("--watch")
        if idx + 1 < len(sys.argv):
            try:
                interval = int(sys.argv[idx + 1])
            except ValueError:
                pass

    if watch:
        print(f"{CYAN}Watching Railway deployments every {interval}s (Ctrl+C to stop)...{RESET}")
        try:
            while True:
                run_scan()
                print(f"{DIM}Next scan in {interval}s...{RESET}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print(f"\n{YELLOW}Monitor stopped.{RESET}")
    else:
        run_scan()


if __name__ == "__main__":
    main()
