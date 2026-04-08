"""
Sandbox Diff — compare resources across two AEP sandboxes.
Uses modules.connection for auth. Never authenticates inline.
"""
from __future__ import annotations

from typing import Any

from modules.connection import connect

from pathlib import Path


def fetch_sandbox_resources(
    environment: str,
    sandbox: str,
) -> dict[str, dict[str, Any]]:
    """
    Connect to a sandbox and fetch all key resources.
    Returns a dict keyed by resource type, each containing {name: details}.
    """
    connect(environment, sandbox=sandbox)

    resources: dict[str, dict[str, Any]] = {}

    # --- Schemas ---
    resources["schemas"] = _fetch_schemas()

    # --- Datasets ---
    resources["datasets"] = _fetch_datasets()

    # --- Segments ---
    resources["segments"] = _fetch_segments()

    # --- Merge Policies ---
    resources["merge_policies"] = _fetch_merge_policies()

    return resources


def _fetch_schemas() -> dict[str, Any]:
    """Fetch all custom (tenant) schemas."""
    try:
        from aepp import schema
        s = schema.Schema()
        raw = s.getSchemas()

        result = {}
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    title = item.get("title", "untitled")
                    result[title] = {
                        "$id": item.get("$id", ""),
                        "class": item.get("meta:class", ""),
                    }
        print(f"    Fetched {len(result)} schemas")
        return result
    except Exception as e:
        print(f"    ⚠️  Could not fetch schemas: {e}")
        return {}


def _fetch_datasets() -> dict[str, Any]:
    """Fetch all datasets."""
    try:
        from aepp import catalog
        c = catalog.Catalog()
        raw = c.getDataSets()

        result = {}
        if isinstance(raw, dict):
            for ds_id, ds in raw.items():
                name = ds.get("name", ds_id)
                result[name] = {
                    "id": ds_id,
                    "schemaRef": ds.get("schemaRef", {}).get("id", ""),
                }
        print(f"    Fetched {len(result)} datasets")
        return result
    except Exception as e:
        print(f"    ⚠️  Could not fetch datasets: {e}")
        return {}


def _fetch_segments() -> dict[str, Any]:
    """Fetch all segment definitions."""
    try:
        from aepp import segmentation
        seg = segmentation.Segmentation()
        raw = seg.getSegments()

        result = {}
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    name = item.get("name", "unnamed")
                    result[name] = {
                        "id": item.get("id", ""),
                        "status": item.get("lifecycleState", ""),
                    }
        elif isinstance(raw, dict):
            for item in raw.get("segments", raw.get("children", [])):
                if isinstance(item, dict):
                    name = item.get("name", "unnamed")
                    result[name] = {
                        "id": item.get("id", ""),
                        "status": item.get("lifecycleState", ""),
                    }
        print(f"    Fetched {len(result)} segments")
        return result
    except Exception as e:
        print(f"    ⚠️  Could not fetch segments: {e}")
        return {}


def _fetch_merge_policies() -> dict[str, Any]:
    """Fetch all merge policies."""
    try:
        from aepp import customerprofile
        cp = customerprofile.Profile()
        raw = cp.getMergePolicies()

        result = {}
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    name = item.get("name", "unnamed")
                    result[name] = {
                        "id": item.get("id", ""),
                        "default": item.get("default", False),
                        "schema": item.get("schema", {}).get("name", ""),
                    }
        print(f"    Fetched {len(result)} merge policies")
        return result
    except Exception as e:
        print(f"    ⚠️  Could not fetch merge policies: {e}")
        return {}
    
def compute_diff(
    resources_a: dict[str, dict[str, Any]],
    resources_b: dict[str, dict[str, Any]],
) -> dict[str, dict[str, set[str]]]:
    """
    Compare two resource dicts and return what's common, only-in-A, only-in-B.
    """
    diff: dict[str, dict[str, set[str]]] = {}

    all_types = set(resources_a.keys()) | set(resources_b.keys())

    for rtype in all_types:
        keys_a = set(resources_a.get(rtype, {}).keys())
        keys_b = set(resources_b.get(rtype, {}).keys())

        diff[rtype] = {
            "in_both": keys_a & keys_b,
            "only_a": keys_a - keys_b,
            "only_b": keys_b - keys_a,
        }

    return diff


def print_diff_report(
    diff: dict[str, dict[str, set[str]]],
    sandbox_a: str,
    sandbox_b: str,
) -> None:
    """Print a formatted diff report using rich tables."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        console.print(Panel(
            f"[bold]Sandbox Diff:[/bold]  [cyan]{sandbox_a}[/cyan]  ↔  [cyan]{sandbox_b}[/cyan]",
            style="bold white",
        ))

        for rtype, result in diff.items():
            label = rtype.replace("_", " ").title()
            in_both = result["in_both"]
            only_a = result["only_a"]
            only_b = result["only_b"]

            table = Table(
                title=f"\n{label}",
                show_header=True,
                header_style="bold magenta",
                title_style="bold yellow",
            )
            table.add_column("Status", style="bold", width=12)
            table.add_column("Count", justify="right", width=8)
            table.add_column("Resources", style="dim")

            # In both
            both_preview = ", ".join(sorted(in_both)[:5])
            if len(in_both) > 5:
                both_preview += f" ... (+{len(in_both) - 5} more)"
            table.add_row("✅ In both", str(len(in_both)), both_preview or "—")

            # Only in A
            a_preview = ", ".join(sorted(only_a)[:5])
            if len(only_a) > 5:
                a_preview += f" ... (+{len(only_a) - 5} more)"
            table.add_row(
                f"🟡 Only {sandbox_a}",
                str(len(only_a)),
                a_preview or "—",
            )

            # Only in B
            b_preview = ", ".join(sorted(only_b)[:5])
            if len(only_b) > 5:
                b_preview += f" ... (+{len(only_b) - 5} more)"
            table.add_row(
                f"🔴 Only {sandbox_b}",
                str(len(only_b)),
                b_preview or "—",
            )

            console.print(table)

        # Summary
        total_only_a = sum(len(r["only_a"]) for r in diff.values())
        total_only_b = sum(len(r["only_b"]) for r in diff.values())
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  {total_only_a} resources only in [cyan]{sandbox_a}[/cyan]")
        console.print(f"  {total_only_b} resources only in [cyan]{sandbox_b}[/cyan]")

    except ImportError:
        # Fallback if rich not available
        _print_diff_plain(diff, sandbox_a, sandbox_b)


def _print_diff_plain(
    diff: dict[str, dict[str, set[str]]],
    sandbox_a: str,
    sandbox_b: str,
) -> None:
    """Plain text fallback if rich is not installed."""
    print(f"\n{'='*60}")
    print(f"  SANDBOX DIFF: {sandbox_a} ↔ {sandbox_b}")
    print(f"{'='*60}")

    for rtype, result in diff.items():
        label = rtype.replace("_", " ").upper()
        print(f"\n  {label}")
        print(f"  {'-'*40}")
        print(f"    ✅ In both:       {len(result['in_both'])}")
        print(f"    🟡 Only {sandbox_a}:  {len(result['only_a'])}")
        for name in sorted(result["only_a"])[:10]:
            print(f"       - {name}")
        print(f"    🔴 Only {sandbox_b}:  {len(result['only_b'])}")
        for name in sorted(result["only_b"])[:10]:
            print(f"       - {name}")

    print(f"\n{'='*60}")
    
def export_to_json(
    diff: dict[str, dict[str, set[str]]],
    resources_a: dict[str, dict[str, Any]],
    resources_b: dict[str, dict[str, Any]],
    sandbox_a: str,
    sandbox_b: str,
    output_path: Path,
) -> None:
    """Export a detailed diff report as a structured JSON file."""
    import json
    from datetime import datetime, timezone

    report = {
        "report_metadata": {
            "title": "AEP Sandbox Diff Report",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "sandbox_a": sandbox_a,
            "sandbox_b": sandbox_b,
        },
        "summary": {},
        "details": {},
    }

    total_in_both = 0
    total_only_a = 0
    total_only_b = 0

    for rtype, result in diff.items():
        in_both = sorted(result["in_both"])
        only_a = sorted(result["only_a"])
        only_b = sorted(result["only_b"])

        total_in_both += len(in_both)
        total_only_a += len(only_a)
        total_only_b += len(only_b)

        # Build detailed entries with metadata from the original resources
        details_both = []
        for name in in_both:
            entry = {"name": name}
            entry[f"{sandbox_a}_details"] = resources_a.get(rtype, {}).get(name, {})
            entry[f"{sandbox_b}_details"] = resources_b.get(rtype, {}).get(name, {})
            details_both.append(entry)

        details_only_a = []
        for name in only_a:
            entry = {"name": name}
            entry["details"] = resources_a.get(rtype, {}).get(name, {})
            details_only_a.append(entry)

        details_only_b = []
        for name in only_b:
            entry = {"name": name}
            entry["details"] = resources_b.get(rtype, {}).get(name, {})
            details_only_b.append(entry)

        report["details"][rtype] = {
            "counts": {
                "in_both": len(in_both),
                f"only_{sandbox_a}": len(only_a),
                f"only_{sandbox_b}": len(only_b),
                "total_unique": len(in_both) + len(only_a) + len(only_b),
            },
            "in_both": details_both,
            f"only_{sandbox_a}": details_only_a,
            f"only_{sandbox_b}": details_only_b,
        }

    report["summary"] = {
        "total_in_both": total_in_both,
        f"total_only_{sandbox_a}": total_only_a,
        f"total_only_{sandbox_b}": total_only_b,
        "total_resources_compared": total_in_both + total_only_a + total_only_b,
        "sync_percentage": round(
            (total_in_both / max(total_in_both + total_only_a + total_only_b, 1)) * 100, 1
        ),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\n  📄 JSON report saved to: {output_path}")


def export_to_csv(
    diff: dict[str, dict[str, set[str]]],
    resources_a: dict[str, dict[str, Any]],
    resources_b: dict[str, dict[str, Any]],
    sandbox_a: str,
    sandbox_b: str,
    output_path: Path,
) -> None:
    """Export a detailed diff report as a CSV file."""
    import csv
    from datetime import datetime, timezone

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header section
        writer.writerow(["AEP Sandbox Diff Report"])
        writer.writerow(["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")])
        writer.writerow(["Sandbox A", sandbox_a])
        writer.writerow(["Sandbox B", sandbox_b])
        writer.writerow([])

        # Summary section
        total_in_both = sum(len(r["in_both"]) for r in diff.values())
        total_only_a = sum(len(r["only_a"]) for r in diff.values())
        total_only_b = sum(len(r["only_b"]) for r in diff.values())
        total = total_in_both + total_only_a + total_only_b
        sync_pct = round((total_in_both / max(total, 1)) * 100, 1)

        writer.writerow(["=== SUMMARY ==="])
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Resources Compared", total])
        writer.writerow(["In Both Sandboxes", total_in_both])
        writer.writerow([f"Only in {sandbox_a}", total_only_a])
        writer.writerow([f"Only in {sandbox_b}", total_only_b])
        writer.writerow(["Sync Percentage", f"{sync_pct}%"])
        writer.writerow([])

        # Per-resource-type summary
        writer.writerow(["=== BREAKDOWN BY RESOURCE TYPE ==="])
        writer.writerow(["Resource Type", "In Both", f"Only {sandbox_a}", f"Only {sandbox_b}", "Total"])
        for rtype, result in diff.items():
            label = rtype.replace("_", " ").title()
            n_both = len(result["in_both"])
            n_a = len(result["only_a"])
            n_b = len(result["only_b"])
            writer.writerow([label, n_both, n_a, n_b, n_both + n_a + n_b])
        writer.writerow([])

        # Detailed listing per resource type
        for rtype, result in diff.items():
            label = rtype.replace("_", " ").upper()
            writer.writerow([f"=== {label} — DETAILED LIST ==="])
            writer.writerow(["Resource Name", "Status", "Sandbox", "Details"])

            for name in sorted(result["in_both"]):
                detail_a = resources_a.get(rtype, {}).get(name, {})
                detail_str = _flatten_details(detail_a)
                writer.writerow([name, "In Both", f"{sandbox_a} & {sandbox_b}", detail_str])

            for name in sorted(result["only_a"]):
                detail = resources_a.get(rtype, {}).get(name, {})
                detail_str = _flatten_details(detail)
                writer.writerow([name, f"Only {sandbox_a}", sandbox_a, detail_str])

            for name in sorted(result["only_b"]):
                detail = resources_b.get(rtype, {}).get(name, {})
                detail_str = _flatten_details(detail)
                writer.writerow([name, f"Only {sandbox_b}", sandbox_b, detail_str])

            writer.writerow([])

    print(f"\n  📄 CSV report saved to: {output_path}")


def _flatten_details(details: dict[str, Any]) -> str:
    """Flatten a details dict into a readable string for CSV."""
    if not details:
        return ""
    parts = []
    for k, v in details.items():
        if isinstance(v, dict):
            v = str(v)
        parts.append(f"{k}={v}")
    return " | ".join(parts)

def export_to_html(
    diff: dict[str, dict[str, set[str]]],
    resources_a: dict[str, dict[str, Any]],
    resources_b: dict[str, dict[str, Any]],
    sandbox_a: str,
    sandbox_b: str,
    output_path: Path,
) -> None:
    """Export a beautiful, self-contained HTML diff report with search and filters."""
    from datetime import datetime, timezone
    import html as html_mod

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    total_both = sum(len(r["in_both"]) for r in diff.values())
    total_a = sum(len(r["only_a"]) for r in diff.values())
    total_b = sum(len(r["only_b"]) for r in diff.values())
    total = total_both + total_a + total_b
    sync_pct = round((total_both / max(total, 1)) * 100, 1)

    def _esc(text: str) -> str:
        return html_mod.escape(str(text))

    # Build resource type cards
    cards_html = ""
    for rtype, result in diff.items():
        label = rtype.replace("_", " ").title()
        n_both = len(result["in_both"])
        n_a = len(result["only_a"])
        n_b = len(result["only_b"])
        r_total = n_both + n_a + n_b
        r_sync = round((n_both / max(r_total, 1)) * 100, 1)

        rows = ""
        for name in sorted(result["in_both"]):
            detail = resources_a.get(rtype, {}).get(name, {})
            detail_str = _esc(" | ".join(f"{k}: {v}" for k, v in detail.items() if not isinstance(v, dict)))
            rows += f'<tr class="resource-row" data-status="both"><td>{_esc(name)}</td><td><span class="badge badge-both">In Both</span></td><td class="detail" title="{detail_str}">{detail_str}</td></tr>\n'
        for name in sorted(result["only_a"]):
            detail = resources_a.get(rtype, {}).get(name, {})
            detail_str = _esc(" | ".join(f"{k}: {v}" for k, v in detail.items() if not isinstance(v, dict)))
            rows += f'<tr class="resource-row" data-status="only-a"><td>{_esc(name)}</td><td><span class="badge badge-a">Only {_esc(sandbox_a)}</span></td><td class="detail" title="{detail_str}">{detail_str}</td></tr>\n'
        for name in sorted(result["only_b"]):
            detail = resources_b.get(rtype, {}).get(name, {})
            detail_str = _esc(" | ".join(f"{k}: {v}" for k, v in detail.items() if not isinstance(v, dict)))
            rows += f'<tr class="resource-row" data-status="only-b"><td>{_esc(name)}</td><td><span class="badge badge-b">Only {_esc(sandbox_b)}</span></td><td class="detail" title="{detail_str}">{detail_str}</td></tr>\n'

        cards_html += f"""
        <div class="card" data-type="{_esc(rtype)}">
            <div class="card-header" onclick="toggleCard(this)">
                <div class="card-title">
                    <h3>{_esc(label)}</h3>
                    <span class="sync-badge" style="background: {'#27ae60' if r_sync > 80 else '#f39c12' if r_sync > 40 else '#e74c3c'}">{r_sync}% synced</span>
                </div>
                <div class="card-stats">
                    <div class="stat"><span class="stat-num">{n_both}</span><span class="stat-label">In Both</span></div>
                    <div class="stat"><span class="stat-num stat-a">{n_a}</span><span class="stat-label">Only {_esc(sandbox_a)}</span></div>
                    <div class="stat"><span class="stat-num stat-b">{n_b}</span><span class="stat-label">Only {_esc(sandbox_b)}</span></div>
                </div>
                <span class="expand-icon">&#9660;</span>
            </div>
            <div class="card-body" style="display:none">
                <table>
                    <thead><tr><th>Resource Name</th><th>Status</th><th>Details</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sandbox Diff: {_esc(sandbox_a)} vs {_esc(sandbox_b)}</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: #0f1117; color: #e1e4e8; padding: 2rem; }}

    .header {{ text-align: center; margin-bottom: 2rem; }}
    .header h1 {{ font-size: 1.8rem; font-weight: 600; margin-bottom: 0.3rem; }}
    .header h1 span {{ color: #58a6ff; }}
    .header .meta {{ color: #8b949e; font-size: 0.85rem; }}
    .header .live-tag {{ display: inline-block; background: #0d3320; color: #3fb950; font-size: 0.7rem; padding: 0.15rem 0.5rem; border-radius: 10px; margin-left: 0.5rem; font-weight: 600; }}

    .search-bar {{ max-width: 700px; margin: 0 auto 1.5rem; display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap; justify-content: center; }}
    .search-input {{ flex: 1; min-width: 250px; padding: 0.7rem 1rem; border-radius: 8px; border: 1px solid #30363d; background: #161b22; color: #e1e4e8; font-size: 0.9rem; outline: none; transition: border 0.2s; }}
    .search-input:focus {{ border-color: #58a6ff; }}
    .search-input::placeholder {{ color: #484f58; }}
    .filter-btns {{ display: flex; gap: 0.4rem; flex-wrap: wrap; }}
    .filter-btn {{ padding: 0.4rem 0.8rem; border-radius: 6px; border: 1px solid #30363d; background: #161b22; color: #8b949e; font-size: 0.78rem; cursor: pointer; transition: all 0.2s; font-weight: 500; }}
    .filter-btn:hover {{ border-color: #58a6ff; color: #e1e4e8; }}
    .filter-btn.active {{ background: #1f6feb; border-color: #1f6feb; color: #fff; }}
    .search-count {{ color: #8b949e; font-size: 0.8rem; text-align: center; margin-bottom: 1rem; }}

    .summary {{ display: flex; gap: 1.2rem; justify-content: center; margin-bottom: 2rem; flex-wrap: wrap; }}
    .summary-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 1.2rem 1.8rem; text-align: center; min-width: 140px; }}
    .summary-card .num {{ font-size: 2rem; font-weight: 700; }}
    .summary-card .label {{ color: #8b949e; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.3rem; }}
    .num-both {{ color: #3fb950; }}
    .num-a {{ color: #d29922; }}
    .num-b {{ color: #f85149; }}
    .num-sync {{ color: {'#3fb950' if sync_pct > 80 else '#d29922' if sync_pct > 40 else '#f85149'}; }}

    .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; margin-bottom: 1rem; overflow: hidden; }}
    .card.hidden {{ display: none; }}
    .card-header {{ padding: 1rem 1.5rem; cursor: pointer; display: flex; align-items: center; width: 100%; }}
    .card-header:hover {{ background: #1c2129; }}
    .card-title {{ display: flex; align-items: center; gap: 0.8rem; width: 250px; flex-shrink: 0; }}
    .card-title h3 {{ font-size: 1.1rem; font-weight: 600; white-space: nowrap; }}
    .sync-badge {{ padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; color: #fff; white-space: nowrap; }}
    .card-stats {{ display: flex; gap: 0; flex: 1; justify-content: center; }}
    .stat {{ text-align: center; width: 120px; }}
    .stat-num {{ display: block; font-size: 1.3rem; font-weight: 700; color: #3fb950; }}
    .stat-a {{ color: #d29922 !important; }}
    .stat-b {{ color: #f85149 !important; }}
    .stat-label {{ font-size: 0.7rem; color: #8b949e; text-transform: uppercase; }}
    .expand-icon {{ color: #8b949e; font-size: 0.8rem; transition: transform 0.2s; width: 30px; text-align: right; flex-shrink: 0; }}
    .card-body {{ padding: 0 1.5rem 1.2rem; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    thead th {{ text-align: left; padding: 0.6rem 0.8rem; border-bottom: 2px solid #30363d; color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }}
    tbody td {{ padding: 0.5rem 0.8rem; border-bottom: 1px solid #21262d; }}
    .badge {{ padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.7rem; font-weight: 600; white-space: nowrap; }}
    .badge-both {{ background: #0d3320; color: #3fb950; }}
    .badge-a {{ background: #341a04; color: #d29922; }}
    .badge-b {{ background: #3d1114; color: #f85149; }}
    .detail {{ color: #8b949e; font-size: 0.78rem; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .resource-row:hover {{ background: #1c2129; }}
    .resource-row.hidden {{ display: none; }}
    .resource-row .highlight {{ background: #58a6ff33; border-radius: 2px; padding: 0 2px; }}

    .footer {{ text-align: center; margin-top: 2rem; color: #484f58; font-size: 0.75rem; }}
    .no-results {{ text-align: center; padding: 2rem; color: #484f58; font-size: 0.9rem; }}
</style>
</head>
<body>
    <div class="header">
        <h1>Sandbox Diff: <span>{_esc(sandbox_a)}</span> ↔ <span>{_esc(sandbox_b)}</span></h1>
        <div class="meta">Generated {generated} &nbsp;|&nbsp; AEP Automation Project <span class="live-tag">LIVE DATA</span></div>
    </div>

    <div class="summary">
        <div class="summary-card"><div class="num" style="color:#e1e4e8">{total}</div><div class="label">Total Resources</div></div>
        <div class="summary-card"><div class="num num-both">{total_both}</div><div class="label">In Both</div></div>
        <div class="summary-card"><div class="num num-a">{total_a}</div><div class="label">Only {_esc(sandbox_a)}</div></div>
        <div class="summary-card"><div class="num num-b">{total_b}</div><div class="label">Only {_esc(sandbox_b)}</div></div>
        <div class="summary-card"><div class="num num-sync">{sync_pct}%</div><div class="label">Sync Rate</div></div>
    </div>

    <div class="search-bar">
        <input type="text" class="search-input" id="searchInput" placeholder="Search resources by name..." oninput="applyFilters()">
        <div class="filter-btns">
            <button class="filter-btn active" data-filter="all" onclick="setFilter(this, 'all')">All</button>
            <button class="filter-btn" data-filter="both" onclick="setFilter(this, 'both')">In Both</button>
            <button class="filter-btn" data-filter="only-a" onclick="setFilter(this, 'only-a')">Only {_esc(sandbox_a)}</button>
            <button class="filter-btn" data-filter="only-b" onclick="setFilter(this, 'only-b')">Only {_esc(sandbox_b)}</button>
        </div>
    </div>
    <div class="search-count" id="searchCount"></div>

    <div id="cardsContainer">
        {cards_html}
    </div>
    <div class="no-results" id="noResults" style="display:none">No resources match your search.</div>

    <div class="footer">AEP Sandbox Diff Report &mdash; Auto-generated from live AEP API data by aep-automation-project</div>

<script>
let activeFilter = 'all';

function toggleCard(header) {{
    const body = header.nextElementSibling;
    const icon = header.querySelector('.expand-icon');
    if (body.style.display === 'none') {{
        body.style.display = 'block';
        icon.style.transform = 'rotate(180deg)';
    }} else {{
        body.style.display = 'none';
        icon.style.transform = 'rotate(0deg)';
    }}
}}

function setFilter(btn, filter) {{
    activeFilter = filter;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilters();
}}

function applyFilters() {{
    const query = document.getElementById('searchInput').value.toLowerCase().trim();
    const rows = document.querySelectorAll('.resource-row');
    let visibleCount = 0;
    let totalCount = rows.length;

    rows.forEach(row => {{
        const name = row.children[0].textContent.toLowerCase();
        const status = row.getAttribute('data-status');
        const matchesSearch = !query || name.includes(query);
        const matchesFilter = activeFilter === 'all' || status === activeFilter;
        const visible = matchesSearch && matchesFilter;
        row.classList.toggle('hidden', !visible);

        // Highlight matching text
        const nameCell = row.children[0];
        const originalName = nameCell.textContent;
        if (query && visible) {{
            const idx = originalName.toLowerCase().indexOf(query);
            if (idx >= 0) {{
                const before = originalName.substring(0, idx);
                const match = originalName.substring(idx, idx + query.length);
                const after = originalName.substring(idx + query.length);
                nameCell.innerHTML = before + '<span class="highlight">' + match + '</span>' + after;
            }}
        }} else {{
            nameCell.textContent = originalName;
        }}

        if (visible) visibleCount++;
    }});

    // Show/hide cards that have no visible rows
    document.querySelectorAll('.card').forEach(card => {{
        const visibleRows = card.querySelectorAll('.resource-row:not(.hidden)');
        card.classList.toggle('hidden', visibleRows.length === 0);
        // Auto-expand cards when searching
        if (query && visibleRows.length > 0) {{
            const body = card.querySelector('.card-body');
            const icon = card.querySelector('.expand-icon');
            body.style.display = 'block';
            icon.style.transform = 'rotate(180deg)';
        }}
    }});

    // Update count
    const countEl = document.getElementById('searchCount');
    const noResults = document.getElementById('noResults');
    if (query || activeFilter !== 'all') {{
        countEl.textContent = `Showing ${{visibleCount}} of ${{totalCount}} resources`;
        noResults.style.display = visibleCount === 0 ? 'block' : 'none';
    }} else {{
        countEl.textContent = '';
        noResults.style.display = 'none';
    }}
}}
</script>
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    print(f"\n  🌐 HTML report saved to: {output_path}")