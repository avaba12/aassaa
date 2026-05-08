import json, sys
from pathlib import Path
from memory.config_manager import ConfigManager

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def _get_api_key() -> str:
    try:
        path = _get_base_dir() / "config" / "api_keys.json"
        return json.loads(path.read_text(encoding="utf-8")).get("gemini_api_key", "")
    except Exception:
        return ""

def _gemini_search(query: str) -> str:
    from google import genai
    client = genai.Client(api_key=_get_api_key())
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=query,
        config={"tools": [{"google_search": {}}]},
    )
    text = ""
    for part in response.candidates[0].content.parts:
        if hasattr(part, "text") and part.text:
            text += part.text
    return text.strip() or "No results."

def _ddg_search(query: str, max_results: int = 6) -> list:
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            results.append({"title": r.get("title", ""), "snippet": r.get("body", ""), "url": r.get("href", "")})
    return results

def _format_ddg(query: str, results: list) -> str:
    if not results:
        return f"No results for: {query}"
    lines = [f"Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        if r.get("title"): lines.append(f"{i}. {r['title']}")
        if r.get("snippet"): lines.append(f"   {r['snippet']}")
        if r.get("url"): lines.append(f"   {r['url']}")
        lines.append("")
    return "\n".join(lines).strip()

def web_search(parameters=None, response=None, player=None, session_memory=None) -> str:
    params = parameters or {}
    query = params.get("query", "").strip()
    if not query:
        return "Please provide a search query, sir."

    if player:
        player.write_log(f"[Search] {query}")

    # Versuche Gemini zuerst
    try:
        result = _gemini_search(query)
        return result
    except Exception as e:
        # Fallback zu DuckDuckGo
        results = _ddg_search(query)
        return _format_ddg(query, results)
