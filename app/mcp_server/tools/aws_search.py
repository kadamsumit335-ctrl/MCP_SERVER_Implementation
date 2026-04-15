import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

AWS_SEARCH_URL = "https://docs.aws.amazon.com/search/doc-search.html"
AWS_BASE_URL = "https://docs.aws.amazon.com"

# Known AWS service doc URL patterns for direct fallback
SERVICE_MAP = {
    "s3": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html",
    "ec2": "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/concepts.html",
    "lambda": "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html",
    "iam": "https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html",
    "rds": "https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html",
    "vpc": "https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html",
    "cloudformation": "https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/Welcome.html",
    "dynamodb": "https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html",
    "appflow": "https://docs.aws.amazon.com/appflow/latest/userguide/what-is-appflow.html",
    "cognito": "https://docs.aws.amazon.com/cognito/latest/developerguide/what-is-amazon-cognito.html",
    "cloudwatch": "https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html",
    "ecs": "https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html",
    "eks": "https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html",
    "sqs": "https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/welcome.html",
    "sns": "https://docs.aws.amazon.com/sns/latest/dg/welcome.html",
    "glue": "https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html",
    "athena": "https://docs.aws.amazon.com/athena/latest/ug/what-is.html",
    "redshift": "https://docs.aws.amazon.com/redshift/latest/mgmt/welcome.html",
    "bedrock": "https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html",
    "sagemaker": "https://docs.aws.amazon.com/sagemaker/latest/dg/whatis.html",
    "authentication": "https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html",
    "auth": "https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html",
}


def search_aws_docs(query: str, max_results: int = 5) -> list[str]:
    """
    Search AWS documentation and return list of relevant URLs.
    Uses AWS search API first, falls back to known service URLs.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # First try: match known service from query keywords
    query_lower = query.lower()
    matched_urls = []
    for service, url in SERVICE_MAP.items():
        if service in query_lower:
            matched_urls.append(url)

    # Second try: AWS search API
    try:
        params = {
            "searchPath": "documentation",
            "searchQuery": query,
            "this_doc_guide": "all",
        }
        response = requests.get(
            AWS_SEARCH_URL, params=params, headers=headers, timeout=15, verify=False
        )
        soup = BeautifulSoup(response.text, "html.parser")
        for item in soup.select("div.lb-content-item a"):
            href = item.get("href", "")
            if href.startswith("http"):
                matched_urls.append(href)
            elif href.startswith("/"):
                matched_urls.append(AWS_BASE_URL + href)
            
            if len(matched_urls) >= max_results:
                break
    except Exception:
        pass

    # Final fallback
    if not matched_urls:
        service_guess = query.split()[0].lower()
        fallback = SERVICE_MAP.get(
            service_guess,
            f"https://docs.aws.amazon.com/{service_guess}/latest/userguide/"
        )
        matched_urls = [fallback]

    return matched_urls[:max_results]

def fetch_page_text(url: str) -> str:
    """
    Fetch an AWS documentation page and return clean readable text.
    Strips nav, headers, footers - keeps only main content.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }
    try:
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["nav", "header", "footer", "script", "style", "aside"]):
            tag.decompose()

        main = (
            soup.find("div", {"id": "main-col-body"})
            or soup.find("div", {"id": "main-content"})
            or soup.find("div", {"id": "awsdocs-content"})
            or soup.find("div", {"id": "aws-topic-content"})
            or soup.find("div", {"class": "awsdocs-container"})
            or soup.find("article")
            or soup.find("main")
            or soup.find("div", {"role": "main"})
            or soup.body
        )

        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        lines = [line for line in text.splitlines() if line.strip()]
        result = "\n".join(lines[:400])

        if not result.strip():
            result = soup.get_text(separator="\n", strip=True)
            lines = [line for line in result.splitlines() if line.strip()]
            result = "\n".join(lines[:400])

        return result if result.strip() else "ERROR: Page content could not be extracted."

    except Exception as exc:
        return f"ERROR fetching page: {exc}"
