"""
Sprint Performance / PF3 — exporter le modèle d'embeddings e5-base en ONNX, une fois.

Même modèle (intfloat/multilingual-e5-base, déjà en cache), mêmes poids, en float32 : seul le
moteur d'exécution change (ONNX Runtime au lieu de torch). Rien n'est téléchargé : le modèle
est lu depuis le cache Hugging Face local. torch n'est nécessaire QUE pour cet export.

    python scripts/export_e5_onnx.py            → models/embeddings/multilingual-e5-base/

Le dossier produit contient model.onnx et tokenizer.json. Atlas ne l'utilise que si
memory.embedding_backend vaut "onnx" dans config/settings.json.
"""

from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = "intfloat/multilingual-e5-base"
OUT = ROOT / "models" / "embeddings" / "multilingual-e5-base"


def main() -> int:
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModel, AutoTokenizer

    src = pathlib.Path(snapshot_download(MODEL, local_files_only=True))
    tok = AutoTokenizer.from_pretrained(src, local_files_only=True)
    model = AutoModel.from_pretrained(src, local_files_only=True).eval()
    OUT.mkdir(parents=True, exist_ok=True)

    enc = tok(["query: exemple de phrase", "passage: un autre exemple, plus long"], padding=True,
              truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        torch.onnx.export(
            model, (enc["input_ids"], enc["attention_mask"]), str(OUT / "model.onnx"),
            input_names=["input_ids", "attention_mask"], output_names=["last_hidden_state"],
            dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"},
                          "last_hidden_state": {0: "batch", 1: "seq"}},
            opset_version=17, do_constant_folding=True,
        )
    shutil.copy2(src / "tokenizer.json", OUT / "tokenizer.json")
    print(f"exporté : {OUT / 'model.onnx'} ({(OUT / 'model.onnx').stat().st_size // (1024 * 1024)} Mo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
