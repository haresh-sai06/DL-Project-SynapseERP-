"""Few-shot product recognition model using metric learning architectures.

Includes a pre-trained ResNet backbone for robust feature extraction 
mapped into a normalized metric embedding space.
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


def require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError("PyTorch is required for product metric learning. Install requirements.txt first.")


class ProductEmbeddingNet(nn.Module if nn is not None else object):
    """Pre-trained CNN backbone that maps product photos into a normalized embedding."""

    def __init__(self, embedding_dim: int = 128, backbone: str = "resnet18") -> None:
        require_torch()
        super().__init__()
        
        try:
            import torchvision.models as models
        except ImportError as exc:
            raise ImportError("torchvision is required. Install torchvision.") from exc
            
        if backbone == "resnet18":
            # Load pre-trained ResNet18
            self.encoder = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
            # Remove the classification head
            in_features = self.encoder.fc.in_features
            self.encoder.fc = nn.Identity()
        else:
            raise ValueError(f"Unsupported backbone: {backbone}")

        # Projection head to our desired embedding dimension
        self.projection = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.ReLU(inplace=True),
            nn.Linear(512, embedding_dim)
        )

    def forward(self, images):  # type: ignore[no-untyped-def]
        require_torch()
        features = self.encoder(images)
        return F.normalize(self.projection(features), dim=-1)


def prototypical_predict(query_embedding, prototypes, rejection_threshold: float = 0.55):  # type: ignore[no-untyped-def]
    """Return nearest prototype label or unknown when similarity is too low."""

    require_torch()
    labels = list(prototypes)
    proto_tensor = torch.stack([prototypes[label] for label in labels])
    similarity = torch.matmul(query_embedding, proto_tensor.T)
    score, index = similarity.max(dim=-1)
    predictions = []
    for value, idx in zip(score.tolist(), index.tolist()):
        predictions.append(labels[idx] if value >= rejection_threshold else "unknown")
    return predictions
