"""Code-mixed order understanding NLP architectures.

Includes a transformer token classification wrapper and a BiLSTM-CRF 
fallback architecture.
"""

from __future__ import annotations

try:
    import torch
    from torch import nn
except Exception:  # pragma: no cover
    torch = None
    nn = None

BIO_TAGS = [
    "O",
    "B-PRODUCT",
    "I-PRODUCT",
    "B-QUANTITY",
    "I-QUANTITY",
    "B-UNIT",
    "I-UNIT",
    "B-PRICE",
    "I-PRICE",
    "B-CUSTOMER",
    "I-CUSTOMER",
]


class MuRILTokenClassifier:
    """Thin wrapper for a MuRIL/IndicBERT token-classification head.

    Kept lazy so the demo pipeline does not download transformer weights.
    """

    def __init__(self, model_name: str = "google/muril-base-cased", num_labels: int = len(BIO_TAGS)) -> None:
        try:
            from transformers import AutoModelForTokenClassification, AutoTokenizer
        except ImportError as exc:  # pragma: no cover
            raise ImportError("Install transformers to use MuRILTokenClassifier.") from exc

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name, num_labels=num_labels)

    def tokenize(self, texts: list[str]):  # type: ignore[no-untyped-def]
        return self.tokenizer(texts, truncation=True, padding=True, return_tensors="pt")


def require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError("PyTorch is required for BiLSTM architecture.")


class BiLSTM_CRF(nn.Module if nn is not None else object):
    """BiLSTM-CRF architecture for token classification.
    
    A robust fallback when heavy transformer models cannot be deployed.
    """

    def __init__(self, vocab_size: int, embedding_dim: int = 128, hidden_dim: int = 128, num_tags: int = len(BIO_TAGS)) -> None:
        require_torch()
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lstm = nn.LSTM(
            embedding_dim, 
            hidden_dim // 2,
            num_layers=1, 
            bidirectional=True, 
            batch_first=True
        )
        self.hidden2tag = nn.Linear(hidden_dim, num_tags)
        
        # We would typically use a CRF layer here (e.g. from torchcrf)
        # but for this skeleton, we will just use a linear projection 
        # and standard cross entropy for simplicity.
        # self.crf = CRF(num_tags, batch_first=True)

    def forward(self, sentence_tokens):  # type: ignore[no-untyped-def]
        require_torch()
        embeds = self.embedding(sentence_tokens)
        lstm_out, _ = self.lstm(embeds)
        emissions = self.hidden2tag(lstm_out)
        return emissions
