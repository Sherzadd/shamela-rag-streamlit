import os
import re
import json
import base64
import webbrowser

from pathlib import Path
from urllib.parse import urlparse, parse_qs

import httpx2

from dotenv import load_dotenv
from pydantic import AnyUrl
from openai import AsyncOpenAI

from mcp import Client
from mcp.client.auth import (
    AuthorizationCodeResult,
    OAuthClientProvider,
)

from mcp.client.streamable_http import (
    streamable_http_client,
)

from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

# =========================================================
# PROJECT CONFIGURATION
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent

ENV_FILE = PROJECT_ROOT / ".env"

if ENV_FILE.exists():
    load_dotenv(ENV_FILE)


SHAMELA_MCP_URL = "https://shamela.link/mcp"

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing."
    )


openai_client = AsyncOpenAI(
    api_key=OPENAI_API_KEY
)


# =========================================================
# SHAMELA AUTH FILE
# =========================================================

SHAMELA_AUTH_FILE = (
    PROJECT_ROOT
    / ".shamela_auth.json"
)


def initialize_cloud_auth():
    """
    Local:
        Uses the existing .shamela_auth.json file.

    Streamlit Cloud:
        Recreates .shamela_auth.json from
        the SHAMELA_AUTH_B64 secret.
    """

    if SHAMELA_AUTH_FILE.exists():
        return

    auth_b64 = os.getenv(
        "SHAMELA_AUTH_B64"
    )

    if not auth_b64:
        return

    try:

        auth_bytes = (
            base64.b64decode(
                auth_b64
            )
        )

        SHAMELA_AUTH_FILE.write_bytes(
            auth_bytes
        )

    except Exception as exc:

        raise RuntimeError(
            "Could not initialize "
            "Shamela authentication."
        ) from exc


initialize_cloud_auth()

# ---------------------------------------------------------
# Persistent Shamela OAuth storage
# ---------------------------------------------------------

SHAMELA_AUTH_FILE = PROJECT_ROOT / ".shamela_auth.json"


class FileTokenStorage:
    def __init__(self, path):
        self.path = Path(path)

    def _read(self):
        if not self.path.exists():
            return {}

        try:
            return json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            return {}

    def _write(self, data):
        self.path.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

    async def get_tokens(self):
        data = self._read()

        if "tokens" not in data:
            return None

        return OAuthToken.model_validate(
            data["tokens"]
        )

    async def set_tokens(self, tokens):
        data = self._read()

        data["tokens"] = tokens.model_dump(
            mode="json"
        )

        self._write(data)

    async def get_client_info(self):
        data = self._read()

        if "client_info" not in data:
            return None

        return OAuthClientInformationFull.model_validate(
            data["client_info"]
        )

    async def set_client_info(self, client_info):
        data = self._read()

        data["client_info"] = client_info.model_dump(
            mode="json"
        )

        self._write(data)


token_storage = FileTokenStorage(
    SHAMELA_AUTH_FILE
)

# ---------------------------------------------------------
# Shamela OAuth
# ---------------------------------------------------------

async def open_browser(url):
    print("\nOpening Shamela authorization page...\n")
    webbrowser.open(str(url))


async def wait_for_callback():
    callback_url = input(
        "\nAfter clicking Allow, copy the full localhost URL "
        "from your browser and paste it here:\n\n"
    ).strip()

    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)

    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]
    issuer = params.get("iss", [None])[0]

    if not code:
        raise RuntimeError(
            "Authorization code was not found in the callback URL."
        )

    return AuthorizationCodeResult(
        code=code,
        state=state,
        iss=issuer
    )

oauth = OAuthClientProvider(
    server_url=SHAMELA_MCP_URL,
    client_metadata=OAuthClientMetadata(
        client_name="Shamela Library Streamlit",
        redirect_uris=[
            AnyUrl("http://localhost:3000/callback")
        ],
    ),
    storage=token_storage,
    redirect_handler=open_browser,
    callback_handler=wait_for_callback,
)

# ---------------------------------------------------------
# Shamela MCP caller
# ---------------------------------------------------------

async def call_shamela(tool_name, arguments):

    async with httpx2.AsyncClient(
        auth=oauth
    ) as http_client:

        transport = streamable_http_client(
            SHAMELA_MCP_URL,
            http_client=http_client
        )

        async with Client(
            transport,
            mode="legacy"
        ) as client:

            result = await client.call_tool(
                tool_name,
                arguments
            )

            return result


async def test_shamela_connection():

    result = await call_shamela(
        "shamela_health",
        {
            "response_format": "json"
        }
    )

    return result.structured_content















# ---------------------------------------------------------
# Query rewriting
# ---------------------------------------------------------

def question_to_search_terms(question):
    text = re.sub(r"[؟?!،,:؛.\-]", " ", question)
    words = text.split()

    stop_words = {
        "ما", "ماذا", "هل", "من", "متى",
        "أين", "كيف", "لماذا", "حكم"
    }

    cleaned_words = []

    for word in words:
        if word in stop_words:
            continue

        if word.startswith(("بال", "وال", "فال", "كال")):
            word = "ال" + word[3:]

        cleaned_words.append(word)

    return " ".join(cleaned_words)


# ---------------------------------------------------------
# Build one RAG source
# ---------------------------------------------------------

async def build_rag_source(hit):
    page_result = await call_shamela(
        "shamela_get_page",
        {
            "book_id": hit["book_id"],
            "page_id": hit["page_id"],
            "response_format": "json"
        }
    )

    page = page_result.structured_content

    citation_result = await call_shamela(
        "shamela_get_citation",
        {
            "book_id": hit["book_id"],
            "page_id": hit["page_id"],
            "style": "shamela",
            "response_format": "json"
        }
    )

    citation = citation_result.structured_content
    components = citation["components"]

    return {
        "book_id": hit["book_id"],
        "page_id": hit["page_id"],
        "book_name": components["book_name"],
        "author_name": components["author_name"],
        "author_death_year": components["death_year"],
        "category": hit.get("category"),
        "printed_page": components["printed_page"],
        "body": page.get("body", ""),
        "footnotes": page.get("foot", ""),
        "citation": citation["formatted"],
        "source_url": components["source_url"]
    }


# ---------------------------------------------------------
# Focused Shamela retrieval
# ---------------------------------------------------------

async def retrieve_focused_rag(
    search_terms,
    top_k=4,
    distance=5,
    fetch_limit=10
):
    search_result = await call_shamela(
        "shamela_search_phrase",
        {
            "query": search_terms,
            "mode": "near",
            "distance": distance,
            "search_in": ["body"],
            "limit": fetch_limit,
            "response_format": "json"
        }
    )

    search_data = search_result.structured_content

    sources = []
    seen_works = set()

    for hit in search_data["results"]:
        source = await build_rag_source(hit)

        work_key = (
            source["author_name"],
            source["book_name"]
        )

        if work_key in seen_works:
            continue

        seen_works.add(work_key)
        sources.append(source)

        if len(sources) >= top_k:
            break

    context_parts = []

    for i, source in enumerate(sources, start=1):
        source_text = f"""
SOURCE {i}

Book: {source["book_name"]}
Author: {source["author_name"]}
Citation: {source["citation"]}
Source URL: {source["source_url"]}

TEXT:
{source["body"]}
"""
        context_parts.append(source_text)

    context = (
        "\n\n" +
        ("\n\n" + "=" * 80 + "\n\n").join(context_parts)
    )

    return {
        "search_terms": search_terms,
        "total_hits": search_data.get("total_hits"),
        "sources": sources,
        "context": context
    }


async def retrieve_question_rag(
    question,
    top_k=4,
    distance=5
):
    search_terms = question_to_search_terms(question)

    result = await retrieve_focused_rag(
        search_terms=search_terms,
        top_k=top_k,
        distance=distance
    )

    result["question"] = question

    return result


# ---------------------------------------------------------
# RAG prompt
# ---------------------------------------------------------

def build_rag_prompt(rag_result):
    return f"""
أنت مساعد بحثي متخصص في تحليل النصوص التراثية.

أجب عن السؤال اعتمادًا فقط على المصادر المسترجعة
من المكتبة الشاملة أدناه.

قواعد مهمة:
1. لا تستخدم معلومات غير موجودة في المصادر.
2. لا تخترع أقوالًا أو مراجع أو صفحات.
3. إذا كانت المصادر غير كافية فقل ذلك بوضوح.
4. فرّق بين قول المؤلف وبين الأقوال التي ينقلها عن غيره.
5. لا تعتبر وجود قول في مصدر واحد إجماعًا.
6. إذا اختلفت المصادر فاذكر الاختلاف بوضوح.
7. عند ذكر معلومة أشِر إلى رقم المصدر مثل [Source 1].
8. استخدم بيانات الاستشهاد الموجودة في المصادر.
9. أجب باللغة العربية بأسلوب واضح ومختصر.

السؤال:
{rag_result["question"]}

المصادر:
{rag_result["context"]}

الإجابة:
"""


# ---------------------------------------------------------
# Evidence verification
# ---------------------------------------------------------

async def verify_rag_answer(
    rag_result,
    draft_answer,
    model="gpt-6.1-sol"
):
    prompt = f"""
أنت مدقق أدلة متخصص في النصوص التراثية العربية.

تحقق من كل دعوى في الإجابة بالاعتماد فقط على
المصادر المسترجعة من المكتبة الشاملة.

السؤال:
{rag_result["question"]}

الإجابة الأولية:
{draft_answer}

المصادر:
{rag_result["context"]}

قواعد التحقق:
1. لا تستخدم أي معرفة خارج المصادر.
2. افحص كل دعوى فقهية أو تاريخية أو نسبة قول إلى عالم.
3. ميّز بين قول المؤلف وقوله المنقول عن غيره.
4. لا تعتبر مناقشة رأي دليلاً على تبنيه.
5. لا تعتبر الاستثناء من الإجماع إجماعاً على الاستثناء.
6. إذا كان الدليل غير كامل استخدم PARTIALLY_SUPPORTED.
7. إذا لم يدعم النص الدعوى استخدم UNSUPPORTED.

القيم المسموحة:
SUPPORTED
PARTIALLY_SUPPORTED
UNSUPPORTED

أعد JSON صحيحاً فقط بهذا الشكل:

{{
  "claims": [
    {{
      "claim": "نص الدعوى",
      "verdict": "SUPPORTED",
      "sources": ["Source 1"],
      "reason": "سبب الحكم"
    }}
  ],
  "corrected_answer": "الإجابة المصححة"
}}
"""

    response = await openai_client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=2200
    )

    raw_text = response.output_text.strip()

    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    elif raw_text.startswith("```"):
        raw_text = raw_text[3:]

    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]

    return json.loads(raw_text.strip())


# ---------------------------------------------------------
# Grounding metrics
# ---------------------------------------------------------

def calculate_grounding_score(verified_result):
    claims = verified_result["claims"]

    scores = {
        "SUPPORTED": 1.0,
        "PARTIALLY_SUPPORTED": 0.5,
        "UNSUPPORTED": 0.0
    }

    total_claims = len(claims)

    supported = sum(
        claim["verdict"] == "SUPPORTED"
        for claim in claims
    )

    partially_supported = sum(
        claim["verdict"] == "PARTIALLY_SUPPORTED"
        for claim in claims
    )

    unsupported = sum(
        claim["verdict"] == "UNSUPPORTED"
        for claim in claims
    )

    if total_claims == 0:
        grounding_score = 0.0
    else:
        grounding_score = sum(
            scores.get(claim["verdict"], 0)
            for claim in claims
        ) / total_claims

    return {
        "total_claims": total_claims,
        "supported": supported,
        "partially_supported": partially_supported,
        "unsupported": unsupported,
        "grounding_score": round(grounding_score, 3)
    }


# ---------------------------------------------------------
# Complete Shamela RAG pipeline
# ---------------------------------------------------------

async def shamela_rag(
    question,
    top_k=4,
    distance=5,
    model="gpt-6.1-sol"
):
    rag_result = await retrieve_question_rag(
        question=question,
        top_k=top_k,
        distance=distance
    )

    prompt = build_rag_prompt(rag_result)

    draft_response = await openai_client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=1600
    )

    draft_answer = draft_response.output_text

    verification = await verify_rag_answer(
        rag_result,
        draft_answer,
        model=model
    )

    metrics = calculate_grounding_score(
        verification
    )

    return {
        "question": question,
        "search_terms": rag_result["search_terms"],
        "sources": rag_result["sources"],
        "draft_answer": draft_answer,
        "verification": verification,
        "grounding_metrics": metrics,
        "final_answer": verification["corrected_answer"]
    }