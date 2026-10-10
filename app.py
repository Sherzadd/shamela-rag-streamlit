import asyncio
import html
import re

import streamlit as st

from shamela_backend import shamela_rag


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="الباحث في المكتبة الشاملة",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# HELPERS
# =========================================================

def safe_text(text):
    return html.escape(
        str(text or "")
    ).replace("\n", "<br>")


def extract_url(value):
    if not value:
        return None

    value = str(value)

    match = re.search(
        r"https?://[^\s\)]+",
        value
    )

    if match:
        return match.group(0)

    return None


# =========================================================
# CSS
# =========================================================

st.html(
    """
    <style>

    /* =====================================================
       GLOBAL PAGE
    ===================================================== */

    .stApp {
        background:
            radial-gradient(
                circle at top right,
                rgba(37, 99, 235, 0.07),
                transparent 30%
            ),
            radial-gradient(
                circle at bottom left,
                rgba(16, 185, 129, 0.05),
                transparent 28%
            ),
            #f8fafc;

        font-family:
            "Noto Naskh Arabic",
            "Segoe UI",
            Tahoma,
            Arial,
            sans-serif;
    }

    .block-container {
        max-width: 1120px;
        padding-top: 1.2rem;
        padding-bottom: 3.5rem;
    }


    /* =====================================================
       HERO
    ===================================================== */

    .hero {
        text-align: center;
        padding: 1.2rem 1rem 1.4rem 1rem;
    }

    .hero-icon {
        font-size: 3rem;
        line-height: 1;
        margin-bottom: 0.5rem;
    }

    .hero-title {
        direction: rtl;
        text-align: center;
        color: #0f172a;
        font-size: 2.65rem;
        font-weight: 800;
        margin: 0;
    }

    .hero-subtitle {
        direction: rtl;
        text-align: center;
        max-width: 700px;
        margin: 0.7rem auto 0 auto;
        color: #64748b;
        font-size: 1.05rem;
        line-height: 1.9;
    }


    /* =====================================================
       SEARCH PANEL
    ===================================================== */

    .search-title {
        direction: rtl;
        text-align: right;
        color: #0f172a;
        font-size: 1.15rem;
        font-weight: 750;
        margin-bottom: 0.6rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 20px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow:
            0 8px 28px
            rgba(15, 23, 42, 0.05);
    }

    div[data-testid="stTextArea"] textarea {
        direction: rtl !important;
        text-align: right !important;

        background: #ffffff !important;
        color: #0f172a !important;

        border: 1px solid #cbd5e1 !important;
        border-radius: 14px !important;

        font-family:
            "Noto Naskh Arabic",
            "Segoe UI",
            Tahoma,
            Arial,
            sans-serif !important;

        font-size: 1.08rem !important;
        line-height: 1.8 !important;

        box-shadow: none !important;
    }

    div[data-testid="stTextArea"] textarea::placeholder {
        direction: rtl;
        text-align: right;
        color: #94a3b8 !important;
    }

    div[data-testid="stTextArea"] textarea:focus {
        border-color: #2563eb !important;
        box-shadow:
            0 0 0 3px
            rgba(37, 99, 235, 0.12)
            !important;
    }


    /* =====================================================
       SEARCH BUTTON
    ===================================================== */

    div[data-testid="stFormSubmitButton"] button {
        background:
            linear-gradient(
                135deg,
                #2563eb,
                #1d4ed8
            ) !important;

        color: #ffffff !important;
        border: none !important;
        border-radius: 13px !important;

        min-height: 3.2rem !important;

        font-size: 1.05rem !important;
        font-weight: 750 !important;

        box-shadow:
            0 5px 14px
            rgba(37, 99, 235, 0.18);

        transition:
            transform 0.15s ease,
            box-shadow 0.15s ease;
    }

    div[data-testid="stFormSubmitButton"] button:hover {
        background:
            linear-gradient(
                135deg,
                #1d4ed8,
                #1e40af
            ) !important;

        transform: translateY(-1px);

        box-shadow:
            0 7px 18px
            rgba(37, 99, 235, 0.22);
    }


    /* =====================================================
       SECTION TITLES
    ===================================================== */

    .section-title {
        direction: rtl;
        text-align: right;

        color: #0f172a;

        font-size: 1.45rem;
        font-weight: 780;

        margin-top: 1.6rem;
        margin-bottom: 0.9rem;
    }

    .section-description {
        direction: rtl;
        text-align: right;

        color: #64748b;

        font-size: 0.95rem;
        line-height: 1.7;

        margin-bottom: 1rem;
    }


    /* =====================================================
       ANSWER CARD
    ===================================================== */

    .answer-card {
        direction: rtl;
        text-align: right;

        background: #ffffff;
        color: #1e293b;

        border: 1px solid #e2e8f0;
        border-right: 5px solid #2563eb;

        border-radius: 18px;

        padding: 1.8rem 2rem;

        font-size: 1.12rem;
        line-height: 2.15;

        box-shadow:
            0 6px 20px
            rgba(15, 23, 42, 0.05);

        margin-bottom: 1.5rem;
    }


    /* =====================================================
       METRICS
    ===================================================== */

    div[data-testid="stMetric"] {
        background: #ffffff;

        border: 1px solid #e2e8f0;
        border-radius: 15px;

        padding: 1rem;

        box-shadow:
            0 3px 10px
            rgba(15, 23, 42, 0.04);
    }

    div[data-testid="stMetricLabel"] {
        font-weight: 650;
    }


    /* =====================================================
       ARABIC TEXT
    ===================================================== */

    .arabic {
        direction: rtl;
        text-align: right;

        color: #1e293b;

        font-family:
            "Noto Naskh Arabic",
            "Segoe UI",
            Tahoma,
            Arial,
            sans-serif;

        font-size: 1.04rem;
        line-height: 2;
    }


    /* =====================================================
       SOURCE CARDS
    ===================================================== */

    .source-book {
        direction: rtl;
        text-align: right;

        color: #0f172a;

        font-size: 1.16rem;
        font-weight: 760;

        margin-bottom: 0.8rem;
    }

    .source-label {
        direction: rtl;
        text-align: right;

        font-weight: 700;

        color: #475569;

        margin-top: 1rem;
    }

    .source-text {
        direction: rtl;
        text-align: right;

        background: #f8fafc;
        color: #334155;

        border-right: 4px solid #2563eb;
        border-radius: 10px;

        padding: 1.2rem;

        margin-top: 0.8rem;

        font-size: 1rem;
        line-height: 2.05;
    }


    /* =====================================================
       VERDICT BADGES
    ===================================================== */

    .badge-supported {
        display: inline-block;

        background: #dcfce7;
        color: #166534;

        border: 1px solid #bbf7d0;
        border-radius: 999px;

        padding: 0.3rem 0.8rem;

        font-size: 0.86rem;
        font-weight: 750;
    }

    .badge-partial {
        display: inline-block;

        background: #fef3c7;
        color: #92400e;

        border: 1px solid #fde68a;
        border-radius: 999px;

        padding: 0.3rem 0.8rem;

        font-size: 0.86rem;
        font-weight: 750;
    }

    .badge-unsupported {
        display: inline-block;

        background: #fee2e2;
        color: #991b1b;

        border: 1px solid #fecaca;
        border-radius: 999px;

        padding: 0.3rem 0.8rem;

        font-size: 0.86rem;
        font-weight: 750;
    }


    /* =====================================================
       CLAIMS
    ===================================================== */

    .claim-text {
        direction: rtl;
        text-align: right;

        color: #1e293b;

        font-size: 1rem;
        line-height: 1.9;

        margin-top: 0.8rem;
    }


    /* =====================================================
       TRUST NOTE
    ===================================================== */

    .trust-note {
        direction: rtl;
        text-align: right;

        color: #64748b;

        font-size: 0.88rem;
        line-height: 1.7;

        margin-top: 0.6rem;
    }


    /* =====================================================
       FOOTER
    ===================================================== */

    .custom-footer {
        text-align: center;

        color: #94a3b8;

        font-size: 0.82rem;

        margin-top: 3rem;

        padding-top: 1.2rem;

        border-top: 1px solid #e2e8f0;
    }


    /* =====================================================
       CLEAN STREAMLIT UI
    ===================================================== */

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    header[data-testid="stHeader"] {
        background: transparent;
    }

    div[data-testid="stToolbar"] {
        visibility: hidden;
        height: 0;
    }

    div[data-testid="stDecoration"] {
        display: none;
    }

    </style>
    """
)


# =========================================================
# SESSION STATE
# =========================================================

if "result" not in st.session_state:
    st.session_state.result = None


# =========================================================
# HERO
# =========================================================

st.html(
    """
    <div class="hero">

        <div class="hero-icon">
            📚
        </div>

        <h1 class="hero-title">
            الباحث في المكتبة الشاملة
        </h1>

        <p class="hero-subtitle">
            مساعد بحثي ذكي يعتمد على مصادر المكتبة الشاملة
            ويقوم بالتحقق من الأدلة ونسبة الأقوال إلى أصحابها
            قبل تقديم الإجابة النهائية.
        </p>

    </div>
    """
)


# =========================================================
# SEARCH AREA
# =========================================================

with st.container(border=True):

    st.html(
        """
        <div class="search-title">
            اسأل في كتب المكتبة الشاملة
        </div>
        """
    )

    with st.form("research_form"):

        question = st.text_area(
            "السؤال",
            label_visibility="collapsed",
            placeholder="مثال: ما حكم الوضوء بالنبيذ؟",
            height=120,
        )

        submitted = st.form_submit_button(
            "🔎 البحث والتحقق",
            use_container_width=True,
        )


# =========================================================
# RUN RAG
# =========================================================

if submitted:

    if not question.strip():

        st.warning(
            "يرجى كتابة السؤال أولاً."
        )

    else:

        with st.spinner(
            "جاري البحث في المكتبة الشاملة وتحليل الأدلة..."
        ):

            try:

                result = asyncio.run(
                    shamela_rag(
                        question.strip()
                    )
                )

                st.session_state.result = result

            except Exception as error:

                st.error(
                    "حدث خطأ أثناء تنفيذ البحث."
                )

                with st.expander(
                    "عرض تفاصيل الخطأ"
                ):

                    st.exception(error)


# =========================================================
# DISPLAY RESULTS
# =========================================================

result = st.session_state.result


if result:

    metrics = result[
        "grounding_metrics"
    ]


    # =====================================================
    # FINAL ANSWER
    # =====================================================

    st.html(
        """
        <div class="section-title">
            ✦ الإجابة الموثقة
        </div>
        """
    )

    final_answer = safe_text(
        result["final_answer"]
    )

    st.html(
        f"""
        <div class="answer-card">
            {final_answer}
        </div>
        """
    )


    # =====================================================
    # TRUST METRICS
    # =====================================================

    st.html(
        """
        <div class="section-title">
            🛡 مستوى توثيق الإجابة
        </div>
        """
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "درجة التوثيق",
        f'{metrics["grounding_score"] * 100:.1f}%'
    )

    col2.metric(
        "✅ مدعوم",
        metrics["supported"]
    )

    col3.metric(
        "⚠️ مدعوم جزئياً",
        metrics[
            "partially_supported"
        ]
    )

    col4.metric(
        "❌ غير مدعوم",
        metrics["unsupported"]
    )

    st.progress(
        metrics["grounding_score"]
    )

    st.html(
        """
        <div class="trust-note">
            درجة التوثيق تعبّر عن مدى دعم
            المصادر المسترجعة للادعاءات الواردة
            في الإجابة، ولا تعني نسبة الصحة
            المطلقة للحكم.
        </div>
        """
    )


    # =====================================================
    # TABS
    # =====================================================

    (
        sources_tab,
        verification_tab,
        technical_tab,
    ) = st.tabs(
        [
            "📚 المصادر",
            "🛡 التحقق من الادعاءات",
            "⚙️ التفاصيل التقنية",
        ]
    )


    # =====================================================
    # SOURCES TAB
    # =====================================================

    with sources_tab:

        sources = result["sources"]

        st.html(
            f"""
            <div class="section-description">
                تم الاستناد إلى
                {len(sources)}
                مصدر/مصادر من المكتبة الشاملة.
            </div>
            """
        )

        for index, source in enumerate(
            sources,
            start=1,
        ):

            book_name = source.get(
                "book_name",
                "مصدر غير معروف",
            )

            author_name = source.get(
                "author_name",
                "غير متوفر",
            )

            citation = source.get(
                "citation",
                "غير متوفر",
            )

            with st.expander(
                f"المصدر {index} — {book_name}",
                expanded=(index == 1),
            ):

                st.html(
                    f"""
                    <div class="source-book">
                        {safe_text(book_name)}
                    </div>
                    """
                )

                info1, info2 = st.columns(2)

                with info1:

                    st.markdown(
                        "**المؤلف:**"
                    )

                    st.write(
                        author_name
                    )

                with info2:

                    st.markdown(
                        "**المرجع:**"
                    )

                    st.write(
                        citation
                    )

                source_url = extract_url(
                    source.get(
                        "source_url"
                    )
                )

                if source_url:

                    st.link_button(
                        "🔗 فتح المصدر في الشاملة",
                        source_url,
                    )

                st.html(
                    """
                    <div class="source-label">
                        النص المسترجع
                    </div>
                    """
                )

                st.html(
                    f"""
                    <div class="source-text">
                        {
                            safe_text(
                                source.get(
                                    "body",
                                    ""
                                )
                            )
                        }
                    </div>
                    """
                )

                footnotes = source.get(
                    "footnotes"
                )

                if footnotes:

                    with st.expander(
                        "عرض الحواشي"
                    ):

                        st.html(
                            f"""
                            <div class="arabic">
                                {
                                    safe_text(
                                        footnotes
                                    )
                                }
                            </div>
                            """
                        )


    # =====================================================
    # VERIFICATION TAB
    # =====================================================

    with verification_tab:

        claims = result[
            "verification"
        ][
            "claims"
        ]

        st.html(
            f"""
            <div class="section-description">
                تم فحص
                {len(claims)}
                ادعاءً في الإجابة النهائية.
            </div>
            """
        )

        for index, claim in enumerate(
            claims,
            start=1,
        ):

            verdict = claim.get(
                "verdict",
                "UNSUPPORTED",
            )

            if verdict == "SUPPORTED":

                badge_class = (
                    "badge-supported"
                )

                badge_text = (
                    "✓ مدعوم"
                )

            elif verdict == (
                "PARTIALLY_SUPPORTED"
            ):

                badge_class = (
                    "badge-partial"
                )

                badge_text = (
                    "⚠ مدعوم جزئياً"
                )

            else:

                badge_class = (
                    "badge-unsupported"
                )

                badge_text = (
                    "✕ غير مدعوم"
                )

            with st.container(
                border=True
            ):

                st.html(
                    f"""
                    <div style="
                        direction: rtl;
                        text-align: right;
                    ">
                        <span class="{badge_class}">
                            {badge_text}
                        </span>
                    </div>
                    """
                )

                st.html(
                    f"""
                    <div class="claim-text">

                        <strong>
                            الدعوى:
                        </strong>

                        <br>

                        {
                            safe_text(
                                claim.get(
                                    "claim",
                                    ""
                                )
                            )
                        }

                    </div>
                    """
                )

                st.html(
                    f"""
                    <div class="claim-text">

                        <strong>
                            سبب الحكم:
                        </strong>

                        <br>

                        {
                            safe_text(
                                claim.get(
                                    "reason",
                                    ""
                                )
                            )
                        }

                    </div>
                    """
                )

                claim_sources = claim.get(
                    "sources",
                    []
                )

                if claim_sources:

                    st.caption(
                        "المصادر: "
                        + ", ".join(
                            claim_sources
                        )
                    )


    # =====================================================
    # TECHNICAL TAB
    # =====================================================

    with technical_tab:

        st.info(
            "هذا القسم مخصص للتفاصيل التقنية "
            "ولا يحتاجه المستخدم العادي."
        )

        st.write(
            "**عبارة البحث المستخدمة:**",
            result["search_terms"],
        )

        st.write(
            "**عدد المصادر المسترجعة:**",
            len(
                result["sources"]
            ),
        )

        st.write(
            "**عدد الادعاءات التي تم فحصها:**",
            metrics[
                "total_claims"
            ],
        )

        st.write(
            "**Grounding score:**",
            metrics[
                "grounding_score"
            ],
        )

        with st.expander(
            "عرض الإجابة الأولية قبل التحقق"
        ):

            st.html(
                f"""
                <div class="arabic">
                    {
                        safe_text(
                            result[
                                "draft_answer"
                            ]
                        )
                    }
                </div>
                """
            )


# =========================================================
# FOOTER
# =========================================================

st.html(
    """
    <div class="custom-footer">

        📚 الباحث في المكتبة الشاملة

        &nbsp; · &nbsp;

        Retrieval-Augmented Generation

        &nbsp; · &nbsp;

        Evidence Verification

    </div>
    """
)