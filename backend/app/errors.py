class ExternalAPIError(Exception):
    """外部API（国会会議録検索API）との通信に失敗した。HTTP 502に対応する。"""

    def __init__(self, message: str = "外部APIとの通信に失敗しました"):
        super().__init__(message)


class LLMError(Exception):
    """Gemini APIの呼び出しまたは応答の解釈に失敗した。HTTP 502に対応する。"""

    def __init__(self, message: str = "AI解析に失敗しました"):
        super().__init__(message)


class NoResultsError(Exception):
    """検索条件に該当する議事録が存在しない。HTTP 404に対応する。"""

    def __init__(self, message: str = "該当する議事録が見つかりませんでした"):
        super().__init__(message)


class CorpusNotReadyError(Exception):
    """コーパスDBが未構築、または必要なインデックスがない。HTTP 409に対応する。"""

    def __init__(self, message: str = "コーパスDBが未構築です"):
        super().__init__(message)
