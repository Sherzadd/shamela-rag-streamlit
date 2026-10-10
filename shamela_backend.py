# =========================================================
# IMPORTS
# =========================================================

import os
import re
import json
import time
import base64
import asyncio
import webbrowser

from pathlib import Path
from urllib.parse import urlparse, parse_qs
from contextlib import asynccontextmanager

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


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing."
    )


DEFAULT_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-6.1-sol"
)


SHAMELA_MCP_URL = (
    "https://shamela.link/mcp"
)


SHAMELA_AUTH_FILE = (
    PROJECT_ROOT / ".shamela_auth.json"
)


SHAMELA_AUTH_B64 = os.getenv(
    "SHAMELA_AUTH_B64"
)


IS_CLOUD = bool(
    SHAMELA_AUTH_B64
)


# =========================================================
# INITIALIZE CLOUD AUTH
# =========================================================

def initialize_cloud_auth():
    """
    On Streamlit Cloud, always initialize the local
    OAuth file from the SHAMELA_AUTH_B64 secret.

    Locally, keep using the existing .shamela_auth.json.
    """

    if SHAMELA_AUTH_B64:
        try:
            auth_bytes = base64.b64decode(
                SHAMELA_AUTH_B64
            )

            SHAMELA_AUTH_FILE.write_bytes(
                auth_bytes
            )

            return

        except Exception as exc:
            raise RuntimeError(
                "Could not initialize Shamela "
                "authentication from SHAMELA_AUTH_B64."
            ) from exc

    if SHAMELA_AUTH_FILE.exists():
        return


# =========================================================
# PERSISTENT TOKEN STORAGE
# =========================================================

class FileTokenStorage:

    def __init__(self, path):
        self.path = Path(path)

    def _read(self):

        if not self.path.exists():
            return {}

        try:
            return json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            json.JSONDecodeError,
            OSError
        ):
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

        tokens = data.get("tokens")

        if not tokens:
            return None

        return OAuthToken.model_validate(
            tokens
        )

    async def set_tokens(
        self,
        tokens
    ):

        data = self._read()

        data["tokens"] = (
            tokens.model_dump(
                mode="json"
            )
        )

        self._write(data)

    async def get_client_info(self):

        data = self._read()

        client_info = data.get(
            "client_info"
        )

        if not client_info:
            return None

        return (
            OAuthClientInformationFull
            .model_validate(
                client_info
            )
        )

    async def set_client_info(
        self,
        client_info
    ):

        data = self._read()

        data["client_info"] = (
            client_info.model_dump(
                mode="json"
            )
        )

        self._write(data)


token_storage = FileTokenStorage(
    SHAMELA_AUTH_FILE
)


# =========================================================
# SHAMELA OAUTH CALLBACKS
# =========================================================

async def open_browser(url):
    """
    Used when local authorization is needed.
    """

    if IS_CLOUD:
        raise RuntimeError(
            "Shamela OAuth credentials need "
            "to be refreshed locally. "
            "Update SHAMELA_AUTH_B64 afterward."
        )

    print(
        "\nOpening Shamela authorization page...\n"
    )

    webbrowser.open(
        str(url)
    )


async def wait_for_callback():
    """
    Local OAuth callback.
    """

    if IS_CLOUD:
        raise RuntimeError(
            "Interactive OAuth cannot run "
            "inside Streamlit Cloud."
        )

    callback_url = input(
        "\nAfter clicking Allow, copy the full "
        "localhost URL from your browser and "
        "paste it here:\n\n"
    ).strip()

    parsed = urlparse(
        callback_url
    )

    params = parse_qs(
        parsed.query
    )

    code = params.get(
        "code",
        [None]
    )[0]

    state = params.get(
        "state",
        [None]
    )[0]

    issuer = params.get(
        "iss",
        [None]
    )[0]

    if not code:
        raise RuntimeError(
            "Authorization code was not "
            "found in callback URL."
        )

    return AuthorizationCodeResult(
        code=code,
        state=state,
        iss=issuer
    )


# =========================================================
# CREATE OAUTH PROVIDER
# =========================================================

def make_oauth_provider():

    return OAuthClientProvider(
        server_url=SHAMELA_MCP_URL,

        client_metadata=OAuthClientMetadata(
            client_name=(
                "Shamela Library Streamlit"
            ),

            redirect_uris=[
                AnyUrl(
                    "http://localhost:3000/callback"
                )
            ],
        ),

        storage=token_storage,

        redirect_handler=open_browser,

        callback_handler=wait_for_callback,
    )


# =========================================================
# SHAMELA MCP SESSION
# =========================================================

@asynccontextmanager
async def shamela_session():
    """
    Open one MCP connection and reuse it
    during the current retrieval request.
    """

    oauth = make_oauth_provider()

    async with httpx2.AsyncClient(
        auth=oauth
    ) as http_client:

        transport = (
            streamable_http_client(
                SHAMELA_MCP_URL,
                http_client=http_client
            )
        )

        async with Client(
            transport,
            mode="legacy"
        ) as client:

            yield client


# =========================================================
# SINGLE SHAMELA CALL
# =========================================================

async def call_shamela(
    tool_name,
    arguments
):

    async with shamela_session() as client:

        return await client.call_tool(
            tool_name,
            arguments
        )


# =========================================================
# HEALTH CHECK
# =========================================================

async def test_shamela_connection():

    result = await call_shamela(
        "shamela_health",
        {
            "response_format": "json"
        }
    )

    return result.structured_content


# =========================================================
# QUERY REWRITING
# =========================================================

def question_to_search_terms(
    question
):
    """
    Convert an Arabic question into simpler
    search terms.
    """

    text = re.sub(
        r"[؟?!،,:؛.\-]",
        " ",
        question
    )

    words = text.split()

    stop_words = {
        "ما",
        "ماذا",
        "هل",
        "من",
        "متى",
        "أين",
        "كيف",
        "لماذا",
        "حكم",
        "ماحكم",
        "في",
        "على",
        "عن",
        "إلى",
        "عند",
    }

    cleaned_words = []

    for word in words:

        if word in stop_words:
            continue

        if word.startswith(
            (
                "بال",
                "وال",
                "فال",
                "كال",
            )
        ):

            word = (
                "ال"
                + word[3:]
            )

        cleaned_words.append(
            word
        )

    search_terms = " ".join(
        cleaned_words
    ).strip()

    if not search_terms:
        search_terms = question.strip()

    return search_terms


# =========================================================
# LIMITED MCP CALL
# =========================================================

async def limited_tool_call(
    client,
    semaphore,
    tool_name,
    arguments
):

    async with semaphore:

        return await client.call_tool(
            tool_name,
            arguments
        )


# =========================================================
# BUILD ONE SOURCE
# =========================================================

async def build_rag_source(
    client,
    hit,
    semaphore
):
    """
    Get page and citation concurrently.
    """

    page_task = limited_tool_call(
        client,
        semaphore,
        "shamela_get_page",
        {
            "book_id": hit["book_id"],
            "page_id": hit["page_id"],
            "response_format": "json"
        }
    )

    citation_task = limited_tool_call(
        client,
        semaphore,
        "shamela_get_citation",
        {
            "book_id": hit["book_id"],
            "page_id": hit["page_id"],
            "style": "shamela",
            "response_format": "json"
        }
    )

    (
        page_result,
        citation_result
    ) = await asyncio.gather(
        page_task,
        citation_task
    )

    page = (
        page_result.structured_content
        or {}
    )

    citation = (
        citation_result.structured_content
        or {}
    )

    components = citation.get(
        "components",
        {}
    )

    return {

        "book_id":
            hit.get("book_id"),

        "page_id":
            hit.get("page_id"),

        "book_name":
            components.get("book_name")
            or hit.get("book_name")
            or "",

        "author_name":
            components.get("author_name")
            or hit.get("author_name")
            or "",

        "author_death_year":
            components.get("death_year"),

        "category":
            hit.get("category"),

        "printed_page":
            components.get(
                "printed_page"
            ),

        "body":
            page.get(
                "body",
                ""
            ),

        "footnotes":
            page.get(
                "foot",
                ""
            ),

        "citation":
            citation.get(
                "formatted",
                ""
            ),

        "source_url":
            components.get(
                "source_url"
            ),
    }


# =========================================================
# SEARCH SHAMELA
# =========================================================

async def search_shamela_hits(
    client,
    search_terms,
    distance=5,
    fetch_limit=8
):
    """
    First try proximity search.
    If nothing is found, use normal page search.
    """

    result = await client.call_tool(
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

    search_data = (
        result.structured_content
        or {}
    )

    if search_data.get(
        "results"
    ):
        return search_data


    # -----------------------------------------------------
    # FALLBACK SEARCH
    # -----------------------------------------------------

    fallback = await client.call_tool(
        "shamela_search_pages",
        {
            "query": search_terms,

            "options": {
                "search_in": [
                    "body"
                ]
            },

            "limit": fetch_limit,

            "response_format": "json"
        }
    )

    return (
        fallback.structured_content
        or {}
    )


# =========================================================
# FOCUSED RETRIEVAL
# =========================================================

async def retrieve_focused_rag(
    search_terms,
    top_k=3,
    distance=5,
    fetch_limit=8
):

    async with shamela_session() as client:

        search_data = (
            await search_shamela_hits(
                client=client,
                search_terms=search_terms,
                distance=distance,
                fetch_limit=fetch_limit
            )
        )

        hits = search_data.get(
            "results",
            []
        )


        # -------------------------------------------------
        # DEDUPLICATION
        # -------------------------------------------------

        unique_hits = []
        seen_works = set()

        for hit in hits:

            book_name = hit.get(
                "book_name"
            )

            author_name = hit.get(
                "author_name"
            )

            if (
                book_name
                or author_name
            ):

                work_key = (
                    author_name,
                    book_name
                )

            else:

                work_key = (
                    "book_id",
                    hit.get("book_id")
                )

            if work_key in seen_works:
                continue

            seen_works.add(
                work_key
            )

            unique_hits.append(
                hit
            )

            if (
                len(unique_hits)
                >= top_k
            ):
                break


        # -------------------------------------------------
        # PARALLEL SOURCE RETRIEVAL
        # -------------------------------------------------

        if unique_hits:

            semaphore = asyncio.Semaphore(
                3
            )

            sources = list(
                await asyncio.gather(
                    *[
                        build_rag_source(
                            client=client,
                            hit=hit,
                            semaphore=semaphore
                        )

                        for hit
                        in unique_hits
                    ]
                )
            )

        else:
            sources = []


    # -----------------------------------------------------
    # BUILD CONTEXT
    # -----------------------------------------------------

    context_parts = []

    for i, source in enumerate(
        sources,
        start=1
    ):

        source_text = f"""
SOURCE {i}

Book: {source["book_name"]}
Author: {source["author_name"]}
Citation: {source["citation"]}
Source URL: {source["source_url"]}

TEXT:
{source["body"]}
"""

        context_parts.append(
            source_text.strip()
        )


    context = (
        "\n\n"
        + (
            "\n\n"
            + "=" * 80
            + "\n\n"
        ).join(
            context_parts
        )
    )


    return {

        "search_terms":
            search_terms,

        "total_hits":
            search_data.get(
                "total_hits"
            ),

        "sources":
            sources,

        "context":
            context,
    }


# =========================================================
# COMPLETE RETRIEVAL FOR QUESTION
# =========================================================

async def retrieve_question_rag(
    question,
    top_k=3,
    distance=5
):

    search_terms = (
        question_to_search_terms(
            question
        )
    )

    result = (
        await retrieve_focused_rag(
            search_terms=search_terms,
            top_k=top_k,
            distance=distance
        )
    )

    result["question"] = question

    return result


# =========================================================
# RAG ANSWER PROMPT
# =========================================================

def build_rag_prompt(
    rag_result
):

    return f"""
أنت مساعد بحثي متخصص في تحليل النصوص التراثية.

أجب عن السؤال اعتمادًا فقط على المصادر المسترجعة
من المكتبة الشاملة أدناه.

قواعد مهمة:

1. لا تستخدم معلومات غير موجودة في المصادر.
2. لا تخترع أقوالًا أو مراجع أو صفحات.
3. إذا كانت المصادر غير كافية للإجابة فقل ذلك بوضوح.
4. فرّق بدقة بين قول المؤلف نفسه وبين الأقوال التي ينقلها.
5. لا تعتبر مجرد مناقشة رأي دليلاً على أن المؤلف يتبناه.
6. لا تعتبر وجود قول في مصدر واحد إجماعًا.
7. لا تعتبر الاستثناء من الإجماع إجماعًا على المستثنى.
8. إذا اختلفت المصادر فاذكر الاختلاف بوضوح.
9. عند ذكر معلومة أشِر إلى المصدر مثل [Source 1].
10. استخدم بيانات الاستشهاد الموجودة في كل مصدر.
11. لا تتجاوز ما تدل عليه النصوص المسترجعة.
12. أجب باللغة العربية بأسلوب واضح ومختصر.

السؤال:

{rag_result["question"]}

المصادر:

{rag_result["context"]}

الإجابة:
"""


# =========================================================
# VERIFICATION JSON SCHEMA
# =========================================================

VERIFICATION_SCHEMA = {
    "type": "object",

    "properties": {

        "claims": {
            "type": "array",

            "items": {
                "type": "object",

                "properties": {

                    "claim": {
                        "type": "string"
                    },

                    "verdict": {
                        "type": "string",

                        "enum": [
                            "SUPPORTED",
                            "PARTIALLY_SUPPORTED",
                            "UNSUPPORTED"
                        ]
                    },

                    "sources": {
                        "type": "array",

                        "items": {
                            "type": "string"
                        }
                    },

                    "reason": {
                        "type": "string"
                    },
                },

                "required": [
                    "claim",
                    "verdict",
                    "sources",
                    "reason"
                ],

                "additionalProperties": False,
            },
        },

        "corrected_answer": {
            "type": "string"
        },
    },

    "required": [
        "claims",
        "corrected_answer"
    ],

    "additionalProperties": False,
}


# =========================================================
# RUN STRUCTURED VERIFICATION
# =========================================================

async def run_verification_request(
    openai_client,
    model,
    prompt,
    max_output_tokens
):

    response = await (
        openai_client.responses.create(
            model=model,

            input=prompt,

            text={
                "format": {
                    "type": "json_schema",
                    "name": (
                        "shamela_verification"
                    ),
                    "schema": (
                        VERIFICATION_SCHEMA
                    ),
                    "strict": True
                }
            },

            max_output_tokens=(
                max_output_tokens
            ),
        )
    )

    return response


# =========================================================
# VERIFY ANSWER
# =========================================================

async def verify_rag_answer(
    openai_client,
    rag_result,
    draft_answer,
    model=DEFAULT_MODEL
):

    prompt = f"""
أنت مدقق أدلة متخصص في النصوص التراثية العربية.

تحقق من الادعاءات المهمة في الإجابة الأولية
بالاعتماد فقط على المصادر المسترجعة من المكتبة الشاملة.

السؤال:

{rag_result["question"]}

الإجابة الأولية:

{draft_answer}

المصادر:

{rag_result["context"]}

قواعد التحقق:

1. لا تستخدم أي معرفة خارج المصادر.

2. افحص الادعاءات الفقهية والتاريخية
   ونسبة الأقوال إلى العلماء.

3. ميّز بدقة بين:
   - قول المؤلف نفسه.
   - قول ينقله عن غيره.
   - اعتراض أو حجة يناقشها.

4. لا تعتبر مناقشة رأي دليلاً على تبنيه.

5. لا تعتبر الاستثناء من الإجماع
   إجماعًا على المستثنى.

6. إذا كان الدليل يدعم جزءًا من الدعوى فقط:
   PARTIALLY_SUPPORTED

7. إذا لم يدعم النص الدعوى:
   UNSUPPORTED

8. إذا دعمها النص بوضوح:
   SUPPORTED

9. اجعل سبب الحكم موجزًا.

10. لا تكرر الادعاءات المتشابهة.

11. افحص أهم الادعاءات فقط، بحد أقصى 12 ادعاءً.

12. corrected_answer يجب أن تعتمد فقط على
    المعلومات التي تدعمها المصادر.

13. لا تستخدم المعرفة العامة لإكمال النقص.
"""


    # -----------------------------------------------------
    # FIRST ATTEMPT
    # -----------------------------------------------------

    response = (
        await run_verification_request(
            openai_client=
                openai_client,

            model=
                model,

            prompt=
                prompt,

            max_output_tokens=
                2400,
        )
    )


    # -----------------------------------------------------
    # RETRY IF INCOMPLETE
    # -----------------------------------------------------

    if getattr(
        response,
        "status",
        None
    ) == "incomplete":

        response = (
            await run_verification_request(
                openai_client=
                    openai_client,

                model=
                    model,

                prompt=
                    prompt,

                max_output_tokens=
                    3600,
            )
        )


    # -----------------------------------------------------
    # VERIFY COMPLETION
    # -----------------------------------------------------

    status = getattr(
        response,
        "status",
        None
    )

    if status not in (
        None,
        "completed"
    ):

        raise RuntimeError(
            "Verification did not complete. "
            f"Status: {status}"
        )


    raw_text = (
        response.output_text
        or ""
    ).strip()

    if not raw_text:

        raise RuntimeError(
            "Verification returned "
            "an empty response."
        )


    try:

        return json.loads(
            raw_text
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "The structured verification "
            "response could not be parsed."
        ) from exc


# =========================================================
# GROUNDING SCORE
# =========================================================

def calculate_grounding_score(
    verified_result
):

    claims = verified_result.get(
        "claims",
        []
    )

    scores = {

        "SUPPORTED":
            1.0,

        "PARTIALLY_SUPPORTED":
            0.5,

        "UNSUPPORTED":
            0.0,
    }


    total_claims = len(
        claims
    )


    supported = sum(
        1
        for claim in claims
        if claim.get(
            "verdict"
        ) == "SUPPORTED"
    )


    partially_supported = sum(
        1
        for claim in claims
        if claim.get(
            "verdict"
        ) == (
            "PARTIALLY_SUPPORTED"
        )
    )


    unsupported = sum(
        1
        for claim in claims
        if claim.get(
            "verdict"
        ) == "UNSUPPORTED"
    )


    if total_claims == 0:

        grounding_score = 0.0

    else:

        score_sum = sum(
            scores.get(
                claim.get(
                    "verdict"
                ),
                0.0
            )

            for claim
            in claims
        )

        grounding_score = (
            score_sum
            / total_claims
        )


    return {

        "total_claims":
            total_claims,

        "supported":
            supported,

        "partially_supported":
            partially_supported,

        "unsupported":
            unsupported,

        "grounding_score":
            round(
                grounding_score,
                3
            ),
    }


# =========================================================
# COMPLETE SHAMELA RAG
# =========================================================

async def shamela_rag(
    question,
    top_k=3,
    distance=5,
    model=DEFAULT_MODEL,
    progress_callback=None
):

    timings = {}

    total_start = (
        time.perf_counter()
    )


    # -----------------------------------------------------
    # PROGRESS HELPER
    # -----------------------------------------------------

    def progress(
        stage,
        message
    ):

        if progress_callback:

            progress_callback(
                stage,
                message
            )


    # =====================================================
    # 1. RETRIEVAL
    # =====================================================

    progress(
        "search",
        "🔍 البحث في فهرس المكتبة الشاملة..."
    )

    retrieval_start = (
        time.perf_counter()
    )


    rag_result = (
        await retrieve_question_rag(
            question=question,
            top_k=top_k,
            distance=distance
        )
    )


    timings[
        "retrieval_seconds"
    ] = round(
        time.perf_counter()
        - retrieval_start,
        2
    )


    progress(
        "sources",
        (
            "📚 تم العثور على "
            f'{len(rag_result["sources"])} '
            "مصادر مناسبة."
        )
    )


    # =====================================================
    # NO SOURCES
    # =====================================================

    if not rag_result[
        "sources"
    ]:

        final_answer = (
            "لم يتم العثور على مصادر كافية "
            "في نتائج البحث للإجابة عن السؤال."
        )

        verification = {
            "claims": [],
            "corrected_answer":
                final_answer
        }

        metrics = (
            calculate_grounding_score(
                verification
            )
        )

        timings[
            "total_seconds"
        ] = round(
            time.perf_counter()
            - total_start,
            2
        )

        progress(
            "complete",
            "✅ اكتمل البحث."
        )

        return {

            "question":
                question,

            "search_terms":
                rag_result[
                    "search_terms"
                ],

            "sources":
                [],

            "draft_answer":
                "",

            "verification":
                verification,

            "grounding_metrics":
                metrics,

            "final_answer":
                final_answer,

            "timings":
                timings,
        }


    # =====================================================
    # 2. BUILD PROMPT
    # =====================================================

    prompt = build_rag_prompt(
        rag_result
    )


    # =====================================================
    # CREATE OPENAI CLIENT
    # =====================================================

    openai_client = AsyncOpenAI(
        api_key=OPENAI_API_KEY
    )


    try:

        # =================================================
        # 3. GENERATE DRAFT
        # =================================================

        progress(
            "generation",
            "✍️ صياغة الإجابة من المصادر المسترجعة..."
        )

        generation_start = (
            time.perf_counter()
        )


        draft_response = (
            await openai_client.responses.create(
                model=model,

                input=prompt,

                max_output_tokens=1200
            )
        )


        draft_answer = (
            draft_response.output_text
            or ""
        )


        timings[
            "generation_seconds"
        ] = round(
            time.perf_counter()
            - generation_start,
            2
        )


        # =================================================
        # 4. VERIFY CLAIMS
        # =================================================

        progress(
            "verification",
            "🛡 التحقق من الادعاءات ومطابقتها بالمصادر..."
        )

        verification_start = (
            time.perf_counter()
        )


        verification = (
            await verify_rag_answer(
                openai_client=
                    openai_client,

                rag_result=
                    rag_result,

                draft_answer=
                    draft_answer,

                model=
                    model
            )
        )


        timings[
            "verification_seconds"
        ] = round(
            time.perf_counter()
            - verification_start,
            2
        )


    finally:

        await openai_client.close()


    # =====================================================
    # 5. GROUNDING METRICS
    # =====================================================

    metrics = (
        calculate_grounding_score(
            verification
        )
    )


    # =====================================================
    # 6. TOTAL TIME
    # =====================================================

    timings[
        "total_seconds"
    ] = round(
        time.perf_counter()
        - total_start,
        2
    )


    progress(
        "complete",
        "✅ اكتمل البحث والتحقق."
    )


    # =====================================================
    # RETURN RESULT
    # =====================================================

    return {

        "question":
            question,

        "search_terms":
            rag_result[
                "search_terms"
            ],

        "sources":
            rag_result[
                "sources"
            ],

        "draft_answer":
            draft_answer,

        "verification":
            verification,

        "grounding_metrics":
            metrics,

        "final_answer":
            verification.get(
                "corrected_answer",
                draft_answer
            ),

        "timings":
            timings,
    }