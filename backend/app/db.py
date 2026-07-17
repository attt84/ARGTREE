"""コーパスDB（SQLite）のアクセス層。

スキーマ:
- speeches      : 発言単位のコーパス本体（国会会議録検索APIのレスポンスを正規化）
- speeches_fts  : 全文検索索引（FTS5 trigram。日本語の部分一致に対応）
- entities      : 明示参照エンティティ（法案・法律・事件・制度など）
- mentions      : 発言→エンティティの言及エッジ
- embeddings    : 発言の埋め込みベクトル（float32 BLOB）

会議・発言者・会派のグラフ構造は speeches のカラム（issue_id, speaker,
speaker_group）から導出できるため、別テーブルには持たない。
"""
import sqlite3
from contextlib import contextmanager

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS speeches (
    speech_id        TEXT PRIMARY KEY,
    issue_id         TEXT,
    session          INTEGER,
    house            TEXT,
    meeting          TEXT,
    issue            TEXT,
    date             TEXT,
    speech_order     INTEGER,
    speaker          TEXT,
    speaker_yomi     TEXT,
    speaker_group    TEXT,
    speaker_position TEXT,
    speaker_role     TEXT,
    speech           TEXT,
    speech_url       TEXT,
    meeting_url      TEXT
);
CREATE INDEX IF NOT EXISTS idx_speeches_date ON speeches(date);
CREATE INDEX IF NOT EXISTS idx_speeches_issue ON speeches(issue_id);

CREATE VIRTUAL TABLE IF NOT EXISTS speeches_fts USING fts5(
    speech_id UNINDEXED,
    speech,
    tokenize='trigram'
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type      TEXT NOT NULL,
    label     TEXT NOT NULL,
    UNIQUE(type, label)
);

CREATE TABLE IF NOT EXISTS mentions (
    speech_id TEXT NOT NULL,
    entity_id INTEGER NOT NULL,
    count     INTEGER DEFAULT 1,
    PRIMARY KEY (speech_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_mentions_entity ON mentions(entity_id);

CREATE TABLE IF NOT EXISTS embeddings (
    speech_id TEXT PRIMARY KEY,
    model     TEXT,
    dim       INTEGER,
    vector    BLOB
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(get_settings().db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def db_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SPEECH_COLUMNS = [
    "speech_id", "issue_id", "session", "house", "meeting", "issue", "date",
    "speech_order", "speaker", "speaker_yomi", "speaker_group",
    "speaker_position", "speaker_role", "speech", "speech_url", "meeting_url",
]


def upsert_speeches(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """発言レコードを保存する。既存IDは無視（再取り込みで重複しない）。FTSも同期する。"""
    inserted = 0
    for row in rows:
        cur = conn.execute(
            f"""INSERT OR IGNORE INTO speeches ({",".join(SPEECH_COLUMNS)})
                VALUES ({",".join("?" for _ in SPEECH_COLUMNS)})""",
            [row.get(c) for c in SPEECH_COLUMNS],
        )
        if cur.rowcount > 0:
            inserted += 1
            conn.execute(
                "INSERT INTO speeches_fts (speech_id, speech) VALUES (?, ?)",
                (row["speech_id"], row.get("speech") or ""),
            )
    return inserted


def fts_search(conn: sqlite3.Connection, terms: str | list[str], limit: int = 20,
               exclude_ids: set[str] | None = None) -> list[sqlite3.Row]:
    """全文検索（複数語はAND）。BM25関連度順に返す。

    trigram索引は3文字以上で有効なため、短い語はLIKE条件として併用する。
    """
    exclude_ids = exclude_ids or set()
    term_list = [terms] if isinstance(terms, str) else list(terms)
    term_list = [t.strip() for t in term_list if t.strip()]
    if not term_list:
        return []

    fts_terms = [t for t in term_list if len(t) >= 3]
    like_terms = [t for t in term_list if len(t) < 3]
    params: list = []
    if fts_terms:
        # フレーズとしてクォートする（記号によるFTS構文エラーを避ける）。並記はAND
        sql = """
            SELECT s.* FROM speeches_fts f
            JOIN speeches s ON s.speech_id = f.speech_id
            WHERE speeches_fts MATCH ?
        """
        params.append(" ".join('"' + t.replace('"', '""') + '"' for t in fts_terms))
        for t in like_terms:
            sql += " AND s.speech LIKE ?"
            params.append(f"%{t}%")
        sql += " ORDER BY rank LIMIT ?"
    else:
        sql = "SELECT * FROM speeches WHERE 1=1"
        for t in like_terms:
            sql += " AND speech LIKE ?"
            params.append(f"%{t}%")
        sql += " ORDER BY date DESC LIMIT ?"
    params.append(limit + len(exclude_ids))
    rows = conn.execute(sql, params).fetchall()
    return [r for r in rows if r["speech_id"] not in exclude_ids][:limit]


def entities_in_text(conn: sqlite3.Connection, text: str,
                     limit: int = 3) -> list[str]:
    """テキストに含まれるエンティティラベルを、具体的（長い）順に返す。

    自然文の問いをグラフの語彙に接続する入口として使う。
    """
    rows = conn.execute(
        """
        SELECT e.label FROM entities e
        WHERE LENGTH(e.label) >= 3 AND instr(?, e.label) > 0
        ORDER BY LENGTH(e.label) DESC
        LIMIT ?
        """,
        (text, limit + 5),
    ).fetchall()
    # 別ラベルの部分文字列は除外する（「高額療養費制度」があれば「療養費制度」は捨てる）
    labels: list[str] = []
    for r in rows:
        if not any(r["label"] in kept for kept in labels):
            labels.append(r["label"])
        if len(labels) >= limit:
            break
    return labels


def speeches_by_entity(conn: sqlite3.Connection, entity_label: str, limit: int = 20,
                       exclude_ids: set[str] | None = None) -> list[sqlite3.Row]:
    """エンティティに言及している発言を、言及回数の多い順→日付降順で返す。"""
    exclude_ids = exclude_ids or set()
    rows = conn.execute(
        """
        SELECT s.* FROM mentions m
        JOIN entities e ON e.entity_id = m.entity_id
        JOIN speeches s ON s.speech_id = m.speech_id
        WHERE e.label = ?
        ORDER BY m.count DESC, s.date DESC LIMIT ?
        """,
        (entity_label, limit + len(exclude_ids)),
    ).fetchall()
    return [r for r in rows if r["speech_id"] not in exclude_ids][:limit]


def entity_neighborhood(conn: sqlite3.Connection, speech_ids: list[str],
                        limit: int = 20) -> list[sqlite3.Row]:
    """指定した発言群が言及しているエンティティを、コーパス全体での言及規模つきで返す。

    マルチホップの「次にどのエンティティを辿るか」の候補リストになる。
    """
    if not speech_ids:
        return []
    placeholders = ",".join("?" for _ in speech_ids)
    return conn.execute(
        f"""
        SELECT e.label, e.type,
               COUNT(DISTINCT m.speech_id) AS local_mentions,
               (SELECT COUNT(*) FROM mentions m2 WHERE m2.entity_id = e.entity_id) AS total_mentions,
               (SELECT MIN(s2.date) FROM mentions m3
                  JOIN speeches s2 ON s2.speech_id = m3.speech_id
                  WHERE m3.entity_id = e.entity_id) AS first_date
        FROM mentions m
        JOIN entities e ON e.entity_id = m.entity_id
        WHERE m.speech_id IN ({placeholders})
        GROUP BY e.entity_id
        ORDER BY local_mentions DESC, total_mentions DESC
        LIMIT ?
        """,
        (*speech_ids, limit),
    ).fetchall()


def corpus_status(conn: sqlite3.Connection) -> dict:
    speech_count = conn.execute("SELECT COUNT(*) FROM speeches").fetchone()[0]
    dates = conn.execute("SELECT MIN(date), MAX(date) FROM speeches").fetchone()
    entity_count = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
    mention_count = conn.execute("SELECT COUNT(*) FROM mentions").fetchone()[0]
    embedding_count = conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]
    return {
        "ready": speech_count > 0,
        "speech_count": speech_count,
        "date_from": dates[0],
        "date_until": dates[1],
        "entity_count": entity_count,
        "mention_count": mention_count,
        "embedding_count": embedding_count,
    }
