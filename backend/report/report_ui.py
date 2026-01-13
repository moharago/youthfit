# backend/report/report_ui.py
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st


def _safe_get(d: Dict[str, Any], key: str, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


def _extract_blocks(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    timeline = _safe_get(report, "timeline", [])
    blocks = {"NOW": None, "PLUS_3M": None, "PLUS_6M": None}

    if isinstance(timeline, list):
        for b in timeline:
            k = _safe_get(b, "key", "")
            if k in blocks:
                blocks[k] = b

    return blocks


def _render_timeline_bar() -> None:
    st.markdown(
        """
        <div style="margin-top: 6px; margin-bottom: 14px;">
          <div style="position: relative; height: 36px;">
            <div style="
              position:absolute; top:16px; left:0; right:0;
              height:6px; border-radius:10px;
              background: rgba(255,255,255,0.35);
            "></div>

            <div style="position:absolute; left:0%; top:6px; transform: translateX(-2px);">
              <div style="width:4px; height:26px; background:#ffffff; border-radius:4px;"></div>
            </div>

            <div style="position:absolute; left:50%; top:6px; transform: translateX(-2px);">
              <div style="width:4px; height:26px; background:#ffffff; border-radius:4px;"></div>
            </div>

            <div style="position:absolute; left:100%; top:6px; transform: translateX(-2px);">
              <div style="width:4px; height:26px; background:#ffffff; border-radius:4px;"></div>
            </div>
          </div>

          <div style="display:flex; justify-content:space-between; font-size: 0.9rem; color: rgba(255,255,255,0.95);">
            <div>지금</div>
            <div>3개월 후</div>
            <div>6개월 후</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def _render_policy_cards(policies: List[Dict[str, Any]]) -> None:
    if not policies:
        st.caption("추천할 정책 카드가 충분하지 않습니다. (추가 상담이 필요할 수 있어요)")
        return

    for p in policies[:2]:
        name = _safe_get(p, "policy_name", "(정책명 없음)")
        why = _safe_get(p, "why_now", "")
        links = _safe_get(p, "links", [])

        st.markdown(
            f"""
            <div style="
              background: white;
              border-radius: 14px;
              padding: 14px 16px;
              margin: 10px 0;
              box-shadow: 0 4px 14px rgba(0,0,0,0.08);
            ">
              <div style="font-weight:700; color:#1e90ff; font-size:1.05rem;">
                {name}
              </div>
              <div style="margin-top:6px; color:#333; font-size:0.92rem; line-height:1.4;">
                {why}
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if isinstance(links, list) and links:
            for link in links[:2]:
                label = _safe_get(link, "label", "공식페이지")
                url = _safe_get(link, "url", None)
                if url:
                    st.link_button(f"🔗 {label}", url)


def render_strategy_report_section(report_payload: Dict[str, Any]) -> None:
    """
    FastAPI 응답 {"session_id":..., "report":..., "meta":...} 렌더
    """
    if not report_payload:
        st.warning("보고서 데이터를 받지 못했습니다.")
        return

    report = _safe_get(report_payload, "report", {})
    header = _safe_get(report, "header", "상담 결과 기반 정책 전략 가이드")
    summary = _safe_get(report, "strategy_summary", "")

    blocks = _extract_blocks(report)

    st.markdown("---")
    st.subheader(header)

    _render_timeline_bar()

    col_now, col_3m, col_6m = st.columns(3)

    with col_now:
        st.markdown("#### ✅ 지금")
        b = blocks.get("NOW") or {}
        policies = _safe_get(b, "policies", [])
        _render_policy_cards(policies if isinstance(policies, list) else [])

    with col_3m:
        st.markdown("#### 🕒 3개월 후")
        b = blocks.get("PLUS_3M") or {}
        policies = _safe_get(b, "policies", [])
        _render_policy_cards(policies if isinstance(policies, list) else [])

    with col_6m:
        st.markdown("#### 🕒 6개월 후")
        b = blocks.get("PLUS_6M") or {}
        policies = _safe_get(b, "policies", [])
        _render_policy_cards(policies if isinstance(policies, list) else [])

    st.markdown("### 요약")
    if summary:
        st.write(summary)
    else:
        st.caption("요약 정보가 없습니다.")

    with st.expander("디버그(meta) 보기", expanded=False):
        st.json(_safe_get(report_payload, "meta", {}))
