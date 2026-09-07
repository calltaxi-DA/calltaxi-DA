from pathlib import Path
import os

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

if load_dotenv is not None:
    load_dotenv(ENV_PATH)
elif ENV_PATH.exists():
    for line in ENV_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        os.environ.setdefault(name, value.strip().strip('"').strip("'"))


def get_env(name: str, required: bool = True) -> str | None:
    value = os.getenv(name)
    if required and not value:
        raise RuntimeError(f"{name} 환경변수가 .env에 설정되어 있지 않습니다.")
    return value


MOBILITY_API_KEY = get_env("MOBILITY_API_KEY", required=False)
MOBILITY_API_BASE_URL = get_env("MOBILITY_API_BASE_URL", required=False) or "https://apis.data.go.kr/B553766/wksn"
