import asyncio
import html
import re

import streamlit as st

from shamela_backend import shamela_rag


st.set_page_config(
    page_title="الباحث في المكتبة الشاملة",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def safe_text(value):
    return html.escape(str(value or "")).replace("\n", "<br>")


def extract_url(value):
    if not value:
        return None

    match = re.search(r"https?://[^\s)]+", str(value))
    return match.group(0) if match else None


st.html(
    """
    <style>

    .stApp {
        background:
            radial-gradient(circle at top right, rgba(37,99,235,.07), transparent 30%),
            radial-gradient(circle at bottom left, rgba(16,185,129,.05), transparent 28%),
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

    .hero {
        text-align: center;
        padding: 1.2rem 1rem 1.4rem;
    }

    .hero-icon {
        font-size: 3rem;
        margin-bottom: .5rem;
    }

    .hero-title {
        direction: rtl;
        text-align: center;

        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;

        font-size: 2.65rem;
        font-weight: 800;

        margin: 0;
    }

    .hero-subtitle {
        direction: rtl;
        text-align: center;

        max-width: 760px;

        margin: .7rem auto 0;

        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;

        font-size: 1.05rem;
        line-height: 1.9;
    }

    .search-title {
        direction: rtl;
        text-align: right;

        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;

        font-size: 1.15rem;
        font-weight: 750;

        margin-bottom: .6rem;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,.94);

        border-radius: 20px !important;
        border: 1px solid #e2e8f0 !important;

        box-shadow:
            0 8px 28px
            rgba(15,23,42,.05);
    }

    div[data-testid="stTextArea"] textarea {
        direction: rtl !important;
        text-align: right !important;

        background: #fff !important;

        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;

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
        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;
    }

    div[data-testid="stFormSubmitButton"] button {
        background:
            linear-gradient(
                135deg,
                #2563eb,
                #1d4ed8
            ) !important;

        color: white !important;
        -webkit-text-fill-color: white !important;

        border: none !important;
        border-radius: 13px !important;

        min-height: 3.2rem !important;

        font-size: 1.05rem !important;
        font-weight: 750 !important;
    }

    .section-title {
        direction: rtl;
        text-align: right;

        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;

        font-size: 1.45rem;
        font-weight: 800;

        margin-top: 1.6rem;
        margin-bottom: .9rem;
    }

    .section-description {
        direction: rtl;
        text-align: right;

        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;

        font-size: .95rem;
        line-height: 1.7;

        margin-bottom: 1rem;
    }

    .answer-card {
        direction: rtl;
        text-align: right;

        background: #fff;

        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;

        border: 1px solid #e2e8f0;
        border-right: 5px solid #2563eb;

        border-radius: 18px;

        padding: 1.8rem 2rem;

        font-size: 1.12rem;
        line-height: 2.15;

        box-shadow:
            0 6px 20px
            rgba(15,23,42,.05);

        margin-bottom: 1.5rem;
    }

    .metrics-grid {
        direction: rtl;

        display: grid;

        grid-template-columns:
            repeat(
                4,
                minmax(0,1fr)
            );

        gap: 1rem;

        margin: .4rem 0 1rem;
    }

    .metric-card {
        background: #fff;

        border:
            1px solid
            #e2e8f0;

        border-radius: 16px;

        padding: 1.15rem 1rem;

        text-align: center;

        box-shadow:
            0 4px 14px
            rgba(15,23,42,.05);
    }

    .metric-card-label {
        color: #475569 !important;
        -webkit-text-fill-color: #475569 !important;

        font-size: .9rem;
        font-weight: 650;

        margin-bottom: .45rem;
    }

    .metric-card-value {
        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;

        font-size: 1.7rem;
        font-weight: 800;

        line-height: 1.2;
    }

    .metric-supported .metric-card-value {
        color: #15803d !important;
        -webkit-text-fill-color: #15803d !important;
    }

    .metric-partial .metric-card-value {
        color: #b45309 !important;
        -webkit-text-fill-color: #b45309 !important;
    }

    .metric-unsupported .metric-card-value {
        color: #dc2626 !important;
        -webkit-text-fill-color: #dc2626 !important;
    }

    .trust-note {
        direction: rtl;
        text-align: right;

        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;

        font-size: .88rem;
        line-height: 1.7;

        margin-top: .6rem;
    }

    .source-book {
        direction: rtl;
        text-align: right;

        color: #0f172a !important;
        -webkit-text-fill-color: #0f172a !important;

        font-size: 1.16rem;
        font-weight: 760;

        margin-bottom: .8rem;
    }

    .source-label {
        direction: rtl;
        text-align: right;

        font-weight: 700;

        color: #475569 !important;
        -webkit-text-fill-color: #475569 !important;

        margin-top: 1rem;
    }

    .source-text {
        direction: rtl;
        text-align: right;

        background: #f8fafc;

        color: #334155 !important;
        -webkit-text-fill-color: #334155 !important;

        border-right:
            4px solid
            #2563eb;

        border-radius: 10px;

        padding: 1.2rem;
        margin-top: .8rem;

        font-size: 1rem;
        line-height: 2.05;
    }

    .arabic {
        direction: rtl;
        text-align: right;

        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;

        font-size: 1.04rem;
        line-height: 2;
    }

    .claim-text {
        direction: rtl;
        text-align: right;

        color: #1e293b !important;
        -webkit-text-fill-color: #1e293b !important;

        font-size: 1rem;
        line-height: 1.9;

        margin-top: .8rem;
    }

    .badge-supported,
    .badge-partial,
    .badge-unsupported {
        display: inline-block;

        border-radius: 999px;

        padding: .3rem .8rem;

        font-size: .86rem;
        font-weight: 750;
    }

    .badge-supported {
        background: #dcfce7;

        color: #166534 !important;
        -webkit-text-fill-color: #166534 !important;

        border:
            1px solid
            #bbf7d0;
    }

    .badge-partial {
        background: #fef3c7;

        color: #92400e !important;
        -webkit-text-fill-color: #92400e !important;

        border:
            1px solid
            #fde68a;
    }

    .badge-unsupported {
        background: #fee2e2;

        color: #991b1b !important;
        -webkit-text-fill-color: #991b1b !important;

        border:
            1px solid
            #fecaca;
    }

    .custom-footer {
        text-align: center;

        color: #94a3b8 !important;
        -webkit-text-fill-color: #94a3b8 !important;

        font-size: .82rem;

        margin-top: 3rem;

        padding-top: 1.2rem;

        border-top:
            1px solid
            #e2e8f0;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    @media (max-width: 768px) {

        .hero-title {
            font-size: 2rem;
        }

        .hero-subtitle {
            font-size: .98rem;
        }

        .answer-card {
            padding: 1.3rem 1.2rem;
            font-size: 1.05rem;
        }

        .metrics-grid {
            grid-template-columns:
                repeat(
                    2,
                    minmax(0,1fr)
                );
        }

        .metric-card-value {
            font-size: 1.4rem;
        }
    }

    </style>
    """
)


if "result" not in st.session_state:
    st.session_state.result = None


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


if submitted:

    if not question.strip():

        st.warning(
            "يرجى كتابة السؤال أولاً."
        )

    else:

        st.session_state.result = None

        status_box = st.status(
            "🔍 البحث في فهرس المكتبة الشاملة...",
            expanded=True,
        )

        def update_progress(
            stage,
            message,
        ):
            if message:
                status_box.write(
                    message
                )

        try:

            result = asyncio.run(
                shamela_rag(
                    question.strip(),
                    top_k=3,
                    progress_callback=
                        update_progress,
                )
            )

            st.session_state.result = (
                result
            )

            status_box.update(
                label=
                    "✅ اكتمل البحث والتحقق",
                state=
                    "complete",
                expanded=
                    False,
            )

        except Exception as error:

            status_box.update(
                label=
                    "حدث خطأ أثناء البحث",
                state=
                    "error",
                expanded=
                    True,
            )

            st.error(
                "حدث خطأ أثناء تنفيذ البحث."
            )

            with st.expander(
                "عرض تفاصيل الخطأ"
            ):

                st.exception(
                    error
                )


result = st.session_state.result


if result:

    metrics = (
        result.get(
            "grounding_metrics",
            {},
        )
        or {}
    )

    grounding_score = float(
        metrics.get(
            "grounding_score",
            0,
        )
        or 0
    )

    grounding_score = max(
        0.0,
        min(
            1.0,
            grounding_score,
        ),
    )

    supported = int(
        metrics.get(
            "supported",
            0,
        )
        or 0
    )

    partially_supported = int(
        metrics.get(
            "partially_supported",
            0,
        )
        or 0
    )

    unsupported = int(
        metrics.get(
            "unsupported",
            0,
        )
        or 0
    )

    total_claims = int(
        metrics.get(
            "total_claims",
            supported
            + partially_supported
            + unsupported,
        )
        or 0
    )


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

    st.html(
        f"""
        <div class="answer-card">

            {
                safe_text(
                    result.get(
                        "final_answer",
                        "",
                    )
                )
            }

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

    grounding_percent = (
        grounding_score
        * 100
    )

    st.html(
        f"""
        <div class="metrics-grid">


            <div class="metric-card">

                <div class="metric-card-label">
                    درجة التوثيق
                </div>

                <div class="metric-card-value">
                    {grounding_percent:.1f}%
                </div>

            </div>


            <div class="
                metric-card
                metric-supported
            ">

                <div class="metric-card-label">
                    ✅ مدعوم
                </div>

                <div class="metric-card-value">
                    {supported}
                </div>

            </div>


            <div class="
                metric-card
                metric-partial
            ">

                <div class="metric-card-label">
                    ⚠️ مدعوم جزئياً
                </div>

                <div class="metric-card-value">
                    {partially_supported}
                </div>

            </div>


            <div class="
                metric-card
                metric-unsupported
            ">

                <div class="metric-card-label">
                    ❌ غير مدعوم
                </div>

                <div class="metric-card-value">
                    {unsupported}
                </div>

            </div>


        </div>
        """
    )

    st.progress(
        grounding_score
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

        sources = (
            result.get(
                "sources",
                [],
            )
            or []
        )

        st.html(
            f"""
            <div class="section-description">

                تم الاستناد إلى
                {len(sources)}
                مصدر/مصادر من المكتبة الشاملة.

            </div>
            """
        )

        if not sources:

            st.info(
                "لم يتم العثور على مصادر لعرضها."
            )

        for index, source in enumerate(
            sources,
            start=1,
        ):

            book_name = (
                source.get(
                    "book_name"
                )
                or
                "مصدر غير معروف"
            )

            author_name = (
                source.get(
                    "author_name"
                )
                or
                "غير متوفر"
            )

            citation = (
                source.get(
                    "citation"
                )
                or
                "غير متوفر"
            )

            printed_page = (
                source.get(
                    "printed_page"
                )
            )

            source_url = extract_url(
                source.get(
                    "source_url"
                )
            )

            with st.expander(
                f"المصدر {index} — {book_name}",
                expanded=
                    (index == 1),
            ):

                st.html(
                    f"""
                    <div class="source-book">

                        {
                            safe_text(
                                book_name
                            )
                        }

                    </div>
                    """
                )

                info1, info2 = (
                    st.columns(2)
                )

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

                if printed_page:

                    st.markdown(
                        "**الصفحة المطبوعة:**"
                    )

                    st.write(
                        printed_page
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
                                    "",
                                )
                            )
                        }

                    </div>
                    """
                )

                footnotes = (
                    source.get(
                        "footnotes"
                    )
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

        verification = (
            result.get(
                "verification",
                {},
            )
            or {}
        )

        claims = (
            verification.get(
                "claims",
                [],
            )
            or []
        )

        st.html(
            f"""
            <div class="section-description">

                تم فحص
                {len(claims)}
                ادعاءً في الإجابة النهائية.

            </div>
            """
        )

        if not claims:

            st.info(
                "لا توجد ادعاءات تفصيلية لعرضها."
            )

        for claim in claims:

            verdict = str(
                claim.get(
                    "verdict",
                    "UNSUPPORTED",
                )
            ).upper()

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
                        direction:rtl;
                        text-align:right;
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
                                    "",
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
                                    "",
                                )
                            )
                        }

                    </div>
                    """
                )

                claim_sources = (
                    claim.get(
                        "sources",
                        [],
                    )
                    or []
                )

                if claim_sources:

                    st.caption(
                        "المصادر: "
                        +
                        ", ".join(
                            str(item)
                            for item
                            in claim_sources
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
            result.get(
                "search_terms",
                "",
            ),
        )

        st.write(
            "**عدد المصادر المسترجعة:**",
            len(
                result.get(
                    "sources",
                    [],
                )
                or []
            ),
        )

        st.write(
            "**عدد الادعاءات التي تم فحصها:**",
            total_claims,
        )

        st.write(
            "**Grounding score:**",
            grounding_score,
        )


        # =================================================
        # PERFORMANCE TIMINGS
        # =================================================

        timings = (
            result.get(
                "timings"
            )
            or {}
        )

        if timings:

            st.markdown(
                "### ⏱ زمن التنفيذ"
            )

            st.write(
                "**استرجاع المصادر:**",
                f'{timings.get("retrieval_seconds", 0)} ثانية',
            )

            st.write(
                "**إنشاء الإجابة:**",
                f'{timings.get("generation_seconds", 0)} ثانية',
            )

            st.write(
                "**التحقق من الادعاءات:**",
                f'{timings.get("verification_seconds", 0)} ثانية',
            )

            st.write(
                "**الوقت الإجمالي:**",
                f'{timings.get("total_seconds", 0)} ثانية',
            )


        # =================================================
        # ORIGINAL DRAFT
        # =================================================

        with st.expander(
            "عرض الإجابة الأولية قبل التحقق"
        ):

            st.html(
                f"""
                <div class="arabic">

                    {
                        safe_text(
                            result.get(
                                "draft_answer",
                                "",
                            )
                        )
                    }

                </div>
                """
            )


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