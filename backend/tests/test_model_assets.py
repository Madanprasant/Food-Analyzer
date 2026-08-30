import json
from pathlib import Path

import torch


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_supplied_checkpoint_matches_class_names() -> None:
    classes = json.loads((PROJECT_ROOT / "ml" / "class_names.json").read_text(encoding="utf-8"))
    checkpoint = torch.load(
        PROJECT_ROOT / "ml" / "models" / "efficientnet_v2_s_indian_food.pth",
        map_location="cpu",
        weights_only=True,
    )
    assert len(classes) == 239
    assert checkpoint["classifier.1.weight"].shape[0] == len(classes)
