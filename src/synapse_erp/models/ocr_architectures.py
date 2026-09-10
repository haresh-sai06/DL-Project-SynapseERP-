"""OCR Architectures for handwritten ledger text.

Includes the baseline CRNN-CTC model and a Transformer-based OCR (TrOCR) skeleton
for advanced handwriting recognition.
"""

from __future__ import annotations

try:
    import torch
    from torch import nn
    import torch.nn.functional as F
except Exception:  # pragma: no cover
    torch = None
    nn = None
    F = None


LEDGER_VOCAB = "0123456789abcdefghijklmnopqrstuvwxyz:/-. rs"
BLANK_INDEX = 0
CHAR_TO_INDEX = {char: idx + 1 for idx, char in enumerate(LEDGER_VOCAB)}
INDEX_TO_CHAR = {idx: char for char, idx in CHAR_TO_INDEX.items()}


def require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError("PyTorch is required for ledger OCR training. Install requirements.txt first.")


class LedgerCRNN(nn.Module if nn is not None else object):
    """CNN visual encoder followed by BiLSTM sequence recognizer."""

    def __init__(self, num_classes: int | None = None, hidden_size: int = 128) -> None:
        require_torch()
        super().__init__()
        num_classes = num_classes or (len(LEDGER_VOCAB) + 1)
        self.cnn = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2)),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2)),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, None)),
        )
        self.rnn = nn.LSTM(
            input_size=128,
            hidden_size=hidden_size,
            num_layers=2,
            bidirectional=True,
            batch_first=False,
            dropout=0.1,
        )
        self.classifier = nn.Linear(hidden_size * 2, num_classes)

    def forward(self, images):  # type: ignore[no-untyped-def]
        require_torch()
        features = self.cnn(images).squeeze(2)
        sequence = features.permute(2, 0, 1)
        encoded, _ = self.rnn(sequence)
        logits = self.classifier(encoded)
        return F.log_softmax(logits, dim=-1)


class TrOCR(nn.Module if nn is not None else object):
    """Transformer-based Optical Character Recognition (TrOCR).
    
    This is an architectural skeleton for future implementation. It uses a Vision 
    Transformer (ViT) encoder and a RoBERTa-based text decoder to auto-regressively 
    generate text directly from an image.
    """

    def __init__(self, encoder_name: str = "microsoft/trocr-small-handwritten", decoder_name: str = "roberta-small") -> None:
        require_torch()
        super().__init__()
        self.encoder_name = encoder_name
        self.decoder_name = decoder_name
        self._is_initialized = False

    def initialize_from_hf(self) -> None:
        """Lazy load HuggingFace models."""
        try:
            from transformers import VisionEncoderDecoderModel
        except ImportError as exc:
            raise ImportError("Install transformers to use TrOCR.") from exc
        
        self.model = VisionEncoderDecoderModel.from_pretrained(self.encoder_name)
        self._is_initialized = True

    def forward(self, pixel_values, decoder_input_ids=None):  # type: ignore[no-untyped-def]
        require_torch()
        if not self._is_initialized:
            self.initialize_from_hf()
        return self.model(pixel_values=pixel_values, decoder_input_ids=decoder_input_ids)


def encode_text(text: str) -> list[int]:
    cleaned = text.lower()
    return [CHAR_TO_INDEX[ch] for ch in cleaned if ch in CHAR_TO_INDEX]


def decode_greedy(log_probs) -> list[str]:  # type: ignore[no-untyped-def]
    require_torch()
    predictions = log_probs.argmax(dim=-1).transpose(0, 1)
    decoded: list[str] = []
    for row in predictions:
        chars: list[str] = []
        last = BLANK_INDEX
        for token in row.tolist():
            if token != BLANK_INDEX and token != last:
                chars.append(INDEX_TO_CHAR.get(token, ""))
            last = token
        decoded.append("".join(chars))
    return decoded
