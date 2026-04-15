import sys
import os
import requests
import re
from mcp.server.fastmcp import FastMCP

# Add parent directory to path to allow imports from app.tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.tools.aws_search import search_aws_docs, fetch_page_text

# Initialize FastMCP server
server = FastMCP("aws-devdocs-server")

# ---- TOOL 1: Search AWS Docs ----
@server.tool()
def search_docs(query: str) -> list[str]:
    """
    Search AWS documentation for a given query.
    Returns a list of relevant AWS documentation URLs.
    """
    return search_aws_docs(query, max_results=5)

# ---- TOOL 2: Fetch AWS Doc Page ----
@server.tool()
def fetch_aws_page(url: str) -> str:
    """
    Fetch an AWS documentation page and return clean readable text.
    Strips navigation, headers, footers – returns only main content.
    """
    return fetch_page_text(url)

# ---- TOOL 3: Extract Relevant Answer ----
@server.tool()
def extract_answer(content: str, query: str) -> str:
    """
    Extract the most relevant paragraphs from AWS doc content
    based on the user query keywords.
    """
    query_words = set(query.lower().split())
    # Split content into paragraphs and filter short ones
    paragraphs = [p.strip() for p in content.split("\n") if len(p.strip()) > 60]
    
    scored = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(1 for word in query_words if word in para_lower)
        if score > 0:
            scored.append((score, para))
            
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [para for _, para in scored[:10]]
    
    return "\n\n".join(top) if top else content[:2000]

# ---- TOOL 4: Search StackOverflow ----
@server.tool()
def search_stackoverflow(query: str) -> str:
    """
    Search StackOverflow for questions and answers related to the query.
    Returns top question titles, answers and links – no API key needed.
    """
    try:
        params = {
            "order": "desc",
            "sort": "relevance",
            "q": query,
            "site": "stackoverflow",
            "pagesize": 3,
            "filter": "withbody" # Includes the body of the answer
        }
        response = requests.get(
            "https://api.stackexchange.com/2.3/search/advanced",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            items = response.json().get("items", [])
            output = []
            for item in items[:3]:
                output.append(f"Q: {item.get('title', '')}")
                # Strip HTML tags from body snippet
                body = item.get("body", "")
                clean_body = re.sub(r"<[^>]+>", "", body)[:300]
                output.append(f"Snippet: {clean_body}")
                output.append("---")
            
            return "\n".join(output) if output else "No StackOverflow results found."
        return f"StackOverflow API error: {response.status_code}"
    except Exception as e:
        return f"Error searching StackOverflow: {e}"

# ---- TOOL 5: Get AWS Pricing ----
@server.tool()
def get_aws_pricing(service: str) -> str:
    """
    Get basic pricing information for an AWS service.
    Returns pricing page URL and summary.
    """
    service_lower = service.lower().replace(" ", "-")
    pricing_url = f"https://aws.amazon.com/pricing/?nc1=h_ls"
    
    pricing_map = {
        "s3": "https://aws.amazon.com/s3/pricing/",
        "ec2": "https://aws.amazon.com/ec2/pricing/",
        "lambda": "https://aws.amazon.com/lambda/pricing/",
        "rds": "https://aws.amazon.com/rds/pricing/",
        "dynamodb": "https://aws.amazon.com/dynamodb/pricing/",
    }
    
    url = pricing_map.get(service_lower, pricing_url)
    return f"Pricing information for {service}:\n{url}\n\nVisit the link for detailed cost dimensions."

if __name__ == "__main__":
    server.run()