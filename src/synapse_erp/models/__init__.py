"""Topic-wise models and architectures.

This package exposes the core perception models, analytics models, and training loops.
"""

from .ocr_architectures import LedgerCRNN, TrOCR
from .vision_architectures import ProductEmbeddingNet
from .nlp_architectures import BIO_TAGS, MuRILTokenClassifier, BiLSTM_CRF
from .forecasting_architectures import LSTMDemandForecaster, TemporalFusionTransformer
from .anomaly_ae import LedgerAnomalyAE
from .knowledge_graph import BusinessGraphSAGE
from .base_trainer import BaseTrainer

__all__ = [
    "LedgerCRNN",
    "TrOCR",
    "ProductEmbeddingNet",
    "BIO_TAGS",
    "MuRILTokenClassifier",
    "BiLSTM_CRF",
    "LSTMDemandForecaster",
    "TemporalFusionTransformer",
    "LedgerAnomalyAE",
    "BusinessGraphSAGE",
    "BaseTrainer"
]
