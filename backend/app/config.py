from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """アプリケーション設定。環境変数または backend/.env で上書きできる。"""

    gemini_api_key: str = ""
    # 生成用モデル（議論木・深掘り・マルチホップの経路判断）
    gemini_model: str = "gemini-3.5-flash"
    # 埋め込みモデルと次元（次元を変えたら埋め込みは全再構築が必要）
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768

    # 埋め込みをVertex AI経由にするか（無料枠の日次上限を回避する）。ADC認証を使うためAPIキー不要
    embedding_use_vertex: bool = False
    gcp_project: str = ""
    gcp_location: str = "us-central1"

    # コーパスDB（SQLite）の置き場所
    db_path: str = str(BACKEND_DIR / "argtree.db")

    kokkai_api_url: str = "https://kokkai.ndl.go.jp/api/speech"
    # 国会APIへの連続リクエスト間隔（秒）。公共APIなので節度を保つ
    kokkai_throttle_seconds: float = 0.6

    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # ライブ検索（/api/search）で取得する発言数
    live_max_records: int = 15
    # プロンプトに注入する議事録テキストの上限文字数
    context_char_limit: int = 30000

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
