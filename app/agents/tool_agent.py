import json
import re
import ast
from typing import Generator

def extract_service_name(query: str) -> str:
    """Extract AWS service name from query."""
    services = ["s3", "ec2", "lambda", "rds", "dynamodb", "iam", "vpc", "ecs", "eks"]
    query_lower = query.lower()
    for service in services:
        if service in query_lower:
            return service
    
    # Default fallback
    words = query.split()
    return words[0] if words else "ec2"

def decide_tools(query: str, available_tools: list) -> list[dict]:
    """
    Analyze the query and decide which tools to call.
    Returns a list of tool calls with their arguments.
    """
    query_lower = query.lower()
    tool_plan = []

    # Rule-based tool selection (can be replaced with LLM reasoning later)

    # If asking about pricing
    if any(word in query_lower for word in ["price", "pricing", "cost", "how much"]):
        # Extract service name
        service = extract_service_name(query)
        tool_plan.append({
            "tool": "get_aws_pricing",
            "args": {"service": service}
        })

    # If asking for code examples
    if any(word in query_lower for word in ["code", "example", "implementation", "how to implement"]):
        tool_plan.append({
            "tool": "search_stackoverflow",
            "args": {"query": query}
        })

    # Always search AWS docs for technical questions
    if not tool_plan or any(word in query_lower for word in ["what", "how", "explain", "configure"]):
        tool_plan.insert(0, {
            "tool": "search_docs",
            "args": {"query": query}
        })

    return tool_plan

def execute_tool_plan(client, tool_plan: list[dict], query: str) -> dict:
    """
    Execute the tool plan and aggregate results.
    Returns combined context from all tool calls.
    """
    results = {
        "docs": "",
        "code": "",
        "pricing": "",
        "sources": []
    }

    for step in tool_plan:
        tool_name = step["tool"]
        args = step["args"]

        if tool_name == "search_docs":
            # Search and fetch docs
            search_res = client.call_tool("search_docs", args)
            urls_raw = search_res.get("result", {}).get("content", [{}])[0].get("text", "")
            
            try:
                url_list = ast.literal_eval(urls_raw) if isinstance(urls_raw, str) else urls_raw
            except:
                url_list = [urls_raw] if urls_raw else []

            if url_list and "ERROR" not in str(url_list[0]):
                results["sources"].extend(url_list)
                # Fetch first URL
                fetch_res = client.call_tool("fetch_aws_page", {"url": url_list[0]})
                page_content = fetch_res.get("result", {}).get("content", [{}])[0].get("text", "")

                if page_content and not page_content.startswith("ERROR"):
                    # Extract relevant parts
                    extract_res = client.call_tool("extract_answer", {
                        "content": page_content,
                        "query": query
                    })
                    results["docs"] = extract_res.get("result", {}).get("content", [{}])[0].get("text", "")

        elif tool_name == "search_stackoverflow":
            so_res = client.call_tool("search_stackoverflow", args)
            results["code"] = so_res.get("result", {}).get("content", [{}])[0].get("text", "")

        elif tool_name == "get_aws_pricing":
            pricing_res = client.call_tool("get_aws_pricing", args)
            results["pricing"] = pricing_res.get("result", {}).get("content", [{}])[0].get("text", "")

    return results

def build_context_from_results(results: dict) -> str:
    """Combine all tool results into a single context string."""
    context_parts = []

    if results["docs"]:
        context_parts.append(f"AWS Documentation:\n{results['docs']}")

    if results["code"]:
        context_parts.append(f"\n\nStackOverflow Examples:\n{results['code']}")

    if results["pricing"]:
        context_parts.append(f"\n\nPricing Information:\n{results['pricing']}")

    return "\n\n".join(context_parts) if context_parts else "No relevant information found."