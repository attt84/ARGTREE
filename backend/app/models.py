from typing import List, Literal, Optional

from pydantic import BaseModel, Field

NodeType = Literal["theme", "pro", "con", "neutral", "solution"]


# ---------------------------------------------------------------------------
# ライブ議論木（/api/search, /api/node_detail）
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., description="検索キーワード（例: '少子化対策'）")
    use_super_search: bool = Field(False, description="AIによるクエリ拡張を使うか")


class ArgumentNode(BaseModel):
    id: str
    label: str
    type: NodeType
    source: Optional[str] = None  # 発言者名など


class ArgumentEdge(BaseModel):
    id: str
    source: str
    target: str


class ArgumentTree(BaseModel):
    nodes: List[ArgumentNode]
    edges: List[ArgumentEdge]


class ArgumentResponse(BaseModel):
    query: str
    expanded_queries: List[str] = []
    tree: ArgumentTree


class NodeDetailRequest(BaseModel):
    query: str
    node_label: str


class NodeDetailResponse(BaseModel):
    node_label: str
    detail_markdown: str


# LLM構造化出力用（クエリ拡張）
class ExpandedQueries(BaseModel):
    queries: List[str] = Field(..., description="元のキーワードを含む検索クエリのリスト")


# ---------------------------------------------------------------------------
# マルチホップ検索（/api/deep_search）
# ---------------------------------------------------------------------------

class DeepSearchRequest(BaseModel):
    query: str = Field(..., description="調べたい問い（例: 'なぜ政治資金規正法が改正されたのか'）")
    max_hops: int = Field(4, ge=1, le=6, description="手繰りの最大ホップ数")


class EvidenceItem(BaseModel):
    speech_id: str
    date: str
    meeting: str
    speaker: str
    speaker_group: Optional[str] = None
    snippet: str
    url: str


class HopStep(BaseModel):
    hop: int
    focus: str          # このホップで何を調べたか（検索語・エンティティ）
    reason: str         # なぜこの焦点に移ったか
    finding: str        # このホップで分かったこと
    evidence: List[EvidenceItem]


class DeepSearchResponse(BaseModel):
    query: str
    steps: List[HopStep]
    synthesis: str      # 鎖全体を統合した解説（Markdown）


# LLM構造化出力用（ホップの意思決定）
class NextFocus(BaseModel):
    query: str = Field(..., description="次に検索すべきキーワード（1〜3語）")
    entity: Optional[str] = Field(None, description="グラフ上で辿るべきエンティティ名（候補にあれば）")
    reason: str = Field(..., description="なぜ次にこれを調べるのか")


class HopDecision(BaseModel):
    finding: str = Field(..., description="現在の証拠から分かったことの要約（2〜4文）")
    evidence_ids: List[str] = Field(..., description="findingの根拠となった発言ID")
    complete: bool = Field(..., description="元の問いに答えるのに十分な情報が揃ったか")
    next_focus: Optional[NextFocus] = Field(None, description="continueする場合の次の焦点")


# ---------------------------------------------------------------------------
# コーパス状態（/api/corpus_status）
# ---------------------------------------------------------------------------

class CorpusStatus(BaseModel):
    ready: bool
    speech_count: int
    date_from: Optional[str] = None
    date_until: Optional[str] = None
    entity_count: int
    mention_count: int
    embedding_count: int
