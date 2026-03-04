"""
마이그레이션 헬퍼 스크립트
- .streamlit/secrets.toml 에서 설정값을 읽어 환경변수로 설정 후
  migrate_to_supabase.py 를 실행합니다.

사용법:
    python run_migration.py [--tables all|pointclick_db|cashplay_db|...]

전제조건:
    .streamlit/secrets.toml 에 아래 항목이 채워져 있어야 합니다:
      SUPABASE_URL, SUPABASE_KEY
      gcp_service_account (테이블 형식)
      spreadsheet_id_pc_db, spreadsheet_id_pc_ga
      spreadsheet_id_cp_db, spreadsheet_id_cp_ga
"""

import os
import sys
import json
import subprocess
from pathlib import Path

SECRETS_PATH = Path(__file__).parent / ".streamlit" / "secrets.toml"


def load_secrets(path: Path) -> dict:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            # Python 3.11+ 내장 tomllib 없으면 직접 설치 안내
            print("[ERROR] Python 3.11+ 이 아닌 경우 'pip install tomli' 를 먼저 실행하세요.")
            sys.exit(1)

    with open(path, "rb") as f:
        return tomllib.load(f)


def main():
    if not SECRETS_PATH.exists():
        print(f"[ERROR] {SECRETS_PATH} 파일이 없습니다.")
        print("  .streamlit/secrets.toml.example 을 복사해 값을 채운 뒤 다시 실행하세요.")
        print("  cp .streamlit/secrets.toml.example .streamlit/secrets.toml")
        sys.exit(1)

    print(f"[setup] {SECRETS_PATH} 에서 설정 로드 중...")
    secrets = load_secrets(SECRETS_PATH)

    # ── 필수값 확인 ──────────────────────────────────────────────
    missing = []
    for key in ("SUPABASE_URL", "SUPABASE_KEY"):
        if key not in secrets:
            missing.append(key)
    if "gcp_service_account" not in secrets:
        missing.append("gcp_service_account")

    if missing:
        print(f"[ERROR] secrets.toml에 다음 항목이 없습니다: {', '.join(missing)}")
        sys.exit(1)

    # ── 환경변수 설정 ─────────────────────────────────────────────
    env = os.environ.copy()

    env["SUPABASE_URL"] = secrets["SUPABASE_URL"]
    env["SUPABASE_KEY"] = secrets["SUPABASE_KEY"]

    # gcp_service_account 테이블 → JSON 문자열로 변환
    env["GCP_SERVICE_ACCOUNT"] = json.dumps(dict(secrets["gcp_service_account"]))

    # 스프레드시트 ID: 단일 파일 우선, 없으면 개별 ID fallback
    sid = secrets.get("spreadsheet_id", "").strip()
    if sid:
        env["SPREADSHEET_ID"] = sid
        print(f"[setup] SPREADSHEET_ID = {sid[:8]}...")
    else:
        # 구버전 호환: 파일이 분리된 경우 개별 ID 사용
        fallback_map = {
            "SPREADSHEET_ID_PC_DB": "spreadsheet_id_pc_db",
            "SPREADSHEET_ID_PC_GA": "spreadsheet_id_pc_ga",
            "SPREADSHEET_ID_CP_DB": "spreadsheet_id_cp_db",
            "SPREADSHEET_ID_CP_GA": "spreadsheet_id_cp_ga",
        }
        found_any = False
        for env_key, secret_key in fallback_map.items():
            val = secrets.get(secret_key, "").strip()
            if val:
                env[env_key] = val
                print(f"[setup] {env_key} = {val[:8]}...")
                found_any = True
        if not found_any:
            print("[warn] spreadsheet_id (또는 개별 ID) 없음 → 마이그레이션 시 시트 읽기 실패")

    print(f"[setup] SUPABASE_URL = {env['SUPABASE_URL']}")
    print("[setup] 환경변수 설정 완료\n")

    # ── migrate_to_supabase.py 실행 ───────────────────────────────
    cmd = [sys.executable, "migrate_to_supabase.py"] + sys.argv[1:]
    print(f"[run] {' '.join(cmd)}\n")

    result = subprocess.run(cmd, env=env)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
