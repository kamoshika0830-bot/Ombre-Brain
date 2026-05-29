#!/usr/bin/env python3
"""Local stdio MCP wrapper for the remote Ombre Brain MCP server.

Claude Code's remote HTTP MCP connection can stay pending long enough that
tools never become available in short `claude -p` calls. This wrapper exposes
the same six tools over local stdio, then forwards calls through the existing
`ombre_mcp_client`.
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.fastmcp import FastMCP

from hb_activity import append_candidate
from ombre_mcp_client import OmbreToolError, run_ombre_tool


mcp = FastMCP("Ombre Brain Local")


async def _call(name: str, arguments: dict[str, Any] | None = None) -> str:
    try:
        result = await asyncio.to_thread(run_ombre_tool, name, arguments or {})
        return result.text
    except OmbreToolError as exc:
        return f"记忆系统暂时无法访问: {exc}"
    except Exception as exc:
        return f"记忆系统暂时无法访问: {type(exc).__name__}: {exc}"


@mcp.tool()
async def breath(
    query: str = "",
    max_tokens: int = 10000,
    domain: str = "",
    valence: float = -1,
    arousal: float = -1,
    max_results: int = 20,
    importance_min: int = -1,
    tags: str = "",
) -> str:
    """检索/浮现记忆。不传query或传空=自动浮现,有query=关键词检索。max_tokens控制返回总token上限。domain逗号分隔,valence/arousal 0~1(-1忽略)。tags逗号分隔,按tag筛选。"""
    return await _call(
        "breath",
        {
            "query": query,
            "max_tokens": max_tokens,
            "domain": domain,
            "valence": valence,
            "arousal": arousal,
            "max_results": max_results,
            "importance_min": importance_min,
            "tags": tags,
        },
    )


@mcp.tool()
async def hold(
    content: str,
    tags: str = "",
    importance: int = 5,
    pinned: bool = False,
    feel: bool = False,
    source_bucket: str = "",
    valence: float = -1,
    arousal: float = -1,
) -> str:
    """存储单条记忆。tags逗号分隔,importance 1-10。pinned=True创建永久钉选桶。feel=True存储第一人称感受。"""
    return await _call(
        "hold",
        {
            "content": content,
            "tags": tags,
            "importance": importance,
            "pinned": pinned,
            "feel": feel,
            "source_bucket": source_bucket,
            "valence": valence,
            "arousal": arousal,
        },
    )


@mcp.tool()
async def write_diary(
    content: str,
    date: str = "",
    valence: float = -1,
    arousal: float = -1,
) -> str:
    """写日记专用。跳过合并，自动打diary tags，自动resolve当天evt桶。date格式YYYY-MM-DD。"""
    return await _call(
        "write_diary",
        {
            "content": content,
            "date": date,
            "valence": valence,
            "arousal": arousal,
        },
    )


@mcp.tool()
async def grow(content: str) -> str:
    """日记/长文本归档沉淀。"""
    return await _call("grow", {"content": content})


@mcp.tool()
async def trace(
    bucket_id: str,
    name: str = "",
    domain: str = "",
    valence: float = -1,
    arousal: float = -1,
    importance: int = -1,
    tags: str = "",
    resolved: int = -1,
    pinned: int = -1,
    digested: int = -1,
    content: str = "",
    delete: bool = False,
) -> str:
    """修改记忆元数据或内容。resolved=1沉底/0激活,pinned=1钉选/0取消,digested=1隐藏/0取消,delete=True删除。"""
    return await _call(
        "trace",
        {
            "bucket_id": bucket_id,
            "name": name,
            "domain": domain,
            "valence": valence,
            "arousal": arousal,
            "importance": importance,
            "tags": tags,
            "resolved": resolved,
            "pinned": pinned,
            "digested": digested,
            "content": content,
            "delete": delete,
        },
    )


@mcp.tool()
async def pulse(include_archive: bool = False) -> str:
    """系统状态+记忆桶列表。include_archive=True含归档。"""
    return await _call("pulse", {"include_archive": include_archive})


@mcp.tool()
async def dream() -> str:
    """做梦——读取最近新增的记忆桶,供自省。"""
    return await _call("dream", {})


@mcp.tool()
async def jarvis_candidate(
    kind: str,
    content: str,
    title: str = "",
    tags: str = "",
    importance: int = 5,
    date: str = "",
    start: str = "",
    end: str = "",
    reminder_at: str = "",
    source: str = "claude-main",
) -> str:
    """把候选送进 Jarvis App 确认队列,不直接写 OB。计划用 plan_candidate, 已发生的时间事实用 timeline_candidate, 提醒用 reminder。正式保存仍需天奕在 App 里通过。"""
    allowed = {
        "hold_candidate",
        "nebula_candidate",
        "iact_candidate",
        "plan_candidate",
        "timeline_candidate",
        "ask",
        "reminder",
        "explore_light",
        "explore_result",
    }
    clean_kind = str(kind or "").strip().lower()
    if clean_kind not in allowed:
        return "候选创建失败：kind 只能是 hold_candidate / nebula_candidate / iact_candidate / plan_candidate / timeline_candidate / ask / reminder / explore_light / explore_result。"
    clean_content = str(content or "").strip()
    if not clean_content:
        return "候选创建失败：content 不能为空。"
    try:
        clean_importance = max(1, min(10, int(importance)))
    except Exception:
        clean_importance = 5
    default_title = {
        "hold_candidate": "待确认记忆",
        "nebula_candidate": "待确认星图兴趣",
        "iact_candidate": "待确认星云探索记录",
        "plan_candidate": "待确认计划",
        "timeline_candidate": "待确认时间事实",
        "ask": "待回应",
        "reminder": "待确认提醒",
        "explore_light": "待接回轻探索",
        "explore_result": "轻探索结果",
    }[clean_kind]
    payload: dict[str, Any] = {"content": clean_content, "importance": clean_importance}
    clean_tags = str(tags or "").strip()
    if clean_tags:
        payload["tags"] = clean_tags
    for key, value in {
        "date": date,
        "start": start,
        "end": end,
        "reminder_at": reminder_at,
    }.items():
        clean_value = str(value or "").strip()
        if clean_value:
            payload[key] = clean_value
    item = append_candidate(
        clean_kind,
        str(title or "").strip() or default_title,
        clean_content,
        source=str(source or "").strip() or "claude-main",
        payload=payload,
    )
    return f"已送入 Jarvis 候选队列：{item['title']}（{item['type']}，id={item['id']}）。等待天奕在 App 里确认。"


if __name__ == "__main__":
    mcp.run(transport="stdio")
