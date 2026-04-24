# fetch_policies.py
# 온통청년 Open API에서 전국 청년 정책 데이터를 가져와 JSON으로 저장

import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ONTONGYOUTH_API_KEY")
BASE_URL = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
PAGE_SIZE = 100
OUTPUT_PATH = "data/files/youth_policies_real.json"


def fetch_page(page_num: int) -> dict:
    params = {
        "apiKeyNm": API_KEY,
        "pageNum": page_num,
        "pageSize": PAGE_SIZE,
        "pageType": "1",   # 1: 목록
        "rtnType": "json",
    }
    res = requests.get(BASE_URL, params=params, timeout=30)
    res.raise_for_status()
    return res.json()


JOB_MAP = {
    "0013001": "재직자", "0013002": "자영업자", "0013003": "미취업자",
    "0013004": "프리랜서", "0013005": "일용근로자", "0013006": "(예비)창업자",
    "0013007": "단기근로자", "0013008": "영농종사자", "0013009": "기타",
    "0013010": "제한없음",
}

INCOME_MAP = {
    "0043001": "무관", "0043002": "연소득 기준", "0043003": "기타",
}

SIDO_MAP = {
    "11": "서울", "21": "부산", "22": "대구", "23": "인천",
    "24": "광주", "25": "대전", "26": "울산", "29": "세종",
    "31": "경기", "32": "강원", "33": "충북", "34": "충남",
    "35": "전북", "36": "전남", "37": "경북", "38": "경남",
    "39": "제주", "50": "제주",
}

def zip_to_region(zip_cd: str) -> str:
    """행정구역코드(5자리) → 시도명. 복수 코드는 첫 번째만 사용."""
    code = (zip_cd or "").split(",")[0].strip()
    return SIDO_MAP.get(code[:2], "전국")


def map_policy(item: dict) -> dict:
    return {
        "policy_id": item.get("plcyNo", ""),
        "policy_name": item.get("plcyNm", ""),
        "policy_category_large": item.get("lclsfNm", ""),
        "policy_category_mid": item.get("mclsfNm", ""),
        "region_name": zip_to_region(item.get("zipCd", "")),
        "target_age_min": item.get("sprtTrgtMinAge", ""),
        "target_age_max": item.get("sprtTrgtMaxAge", ""),
        "target_employment_status": JOB_MAP.get(item.get("jobCd", ""), item.get("jobCd", "")),
        "target_income_level": INCOME_MAP.get(item.get("earnCndSeCd", ""), item.get("earnCndSeCd", "")),
        "summary": item.get("plcyExplnCn", ""),
        "support_content": item.get("plcySprtCn", ""),
        "application_method": item.get("plcyAplyMthdCn", ""),
        "agency_name": item.get("sprvsnInstCdNm", "") or item.get("rgtrInstCdNm", ""),
        "keywords": [
            kw.strip()
            for kw in (item.get("plcyKywdNm", "") or "").split(",")
            if kw.strip()
        ],
    }


def fetch_all():
    if not API_KEY:
        raise ValueError("ONTONGYOUTH_API_KEY가 .env에 없습니다.")

    all_policies = []
    page = 1

    print("🔄 온통청년 API 데이터 수집 시작...")

    while True:
        print(f"  📄 페이지 {page} 요청 중...", end=" ")
        data = None
        for attempt in range(3):
            try:
                data = fetch_page(page)
                break
            except Exception as e:
                print(f"\n⚠️  page {page} 시도 {attempt+1}/3 실패: {e}")
                if attempt < 2:
                    time.sleep(3)
        if data is None:
            print(f"❌ page {page} 최종 실패, 중단합니다.")
            break

        # 응답 구조 첫 페이지에서 출력 (필드명 확인용)
        if page == 1:
            print(f"\n📦 응답 최상위 키: {list(data.keys())}")
            print(f"📦 resultCode: {data.get('resultCode')}")
            print(f"📦 resultMessage: {data.get('resultMessage')}")
            result = data.get("result")
            print(f"📦 result 타입: {type(result)}")
            if isinstance(result, dict):
                print(f"📦 result 키: {list(result.keys())}")
                for k, v in result.items():
                    if isinstance(v, list) and v:
                        print(f"📦 result['{k}'] 첫 번째 항목 필드: {list(v[0].keys())}")
            elif isinstance(result, list) and result:
                print(f"📦 result 첫 번째 항목 필드: {list(result[0].keys())}")
            print()

        result = data.get("result", {})
        items = result.get("youthPolicyList", [])
        pagging = result.get("pagging", {})
        if not items:
            print("완료 (데이터 없음)")
            break

        all_policies.extend([map_policy(item) for item in items])
        print(f"{len(items)}건 수집 (누적: {len(all_policies)}건)")

        # 마지막 페이지 확인
        if page == 1:
            print(f"📊 pagging 정보: {pagging}")
        total_count = int(pagging.get("totCount", 0) or pagging.get("totCnt", 0) or 0)
        if total_count and len(all_policies) >= total_count:
            break
        if len(items) < PAGE_SIZE:
            break

        page += 1
        time.sleep(1.5)  # API 과부하 방지

    print(f"\n✅ 총 {len(all_policies)}개 정책 수집 완료")
    return all_policies


def save(policies: list):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"policies": policies}, f, ensure_ascii=False, indent=2)
    print(f"💾 저장 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    policies = fetch_all()
    if policies:
        save(policies)
        print("\n다음 단계: python ingest.py 실행")
    else:
        print("❌ 수집된 정책이 없습니다. API 키와 응답을 확인하세요.")
