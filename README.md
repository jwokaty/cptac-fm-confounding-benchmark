# TITAN vs mSTAR Benchmark

Feature extraction pipeline for comparing TITAN and mSTAR whole-slide image foundation models on CPTAC-BRCA and CPTAC-UCEC.

Slide embeddings are evaluated using [Patho-Bench](https://github.com/mahmoodlab/Patho-Bench) on mutation prediction and immune classification tasks.

---

## Overview

| Model | Pipeline | Patch size | Magnification | Pooling |
|---|---|---|---|---|
| TITAN | TRIDENT (segmentation → tiling → CONCH v1.5 → TITAN) | 512×512 | 20× | TITAN slide encoder |
| mSTAR | CLAM (segmentation → tiling) → mSTAR feature extraction → mean pool | 256×256 | 20× | Mean pooling |

**Why CPTAC only (not TCGA):** mSTAR was pretrained on ~22k TCGA slides. Evaluating on TCGA would inflate its apparent performance unfairly. Both models are evaluated on CPTAC-BRCA (122 patients) and CPTAC-UCEC (95 patients).

---

## Tasks (via Patho-Bench)

| Dataset | Tasks |
|---|---|
| CPTAC-BRCA | PIK3CA_mutation, TP53_mutation, Immune_class |
| CPTAC-UCEC | PTEN_mutation, CTNNB1_mutation, Immune_class |

---

## Requirements

- Python 3.10 or 3.11
- [uv](https://github.com/astral-sh/uv)
- GPU with ≥24GB VRAM (A100 recommended)
- [ascli](https://www.ibm.com/aspera/connect/) for CPTAC slide download
- HuggingFace account with access to [TITAN](https://huggingface.co/MahmoodLab/TITAN) and [mSTAR](https://huggingface.co/Wangyh/mSTAR)

---

## Setup

```bash
git clone https://github.com/<your-username>/titan-mstar-benchmark.git
cd titan-mstar-benchmark/extraction
cp .env.example .env   # fill in HF_TOKEN and Aspera URLs
uv sync
```

---

## Running the pipeline

Run scripts in this order:

```bash
# 1. Download mSTAR model weights from HuggingFace
uv run python src/benchmark/scripts/download_weights.py

# 2. Download CPTAC slides via Aspera
uv run python src/benchmark/scripts/download_cptac.py

# 3. TITAN: segmentation + tiling + CONCH v1.5 features + TITAN slide pooling
bash scripts/extract_titan_features.sh

# 4. mSTAR: CLAM segmentation + tiling
bash scripts/clam_segment_patch_mstar.sh

# 5. mSTAR: patch feature extraction
bash scripts/extract_mstar_features.sh

# 6. mSTAR: mean pool patch features into slide embeddings
uv run python src/benchmark/scripts/pool_mstar.py

# 7. Compress outputs before shutting down instance
bash scripts/save_outputs.sh
```

---

## Outputs

```
data/
  trident/
    cptac_brca/20x_512px/slide_features_titan/   # TITAN slide embeddings (.h5)
    cptac_ucec/20x_512px/slide_features_titan/
  slide_embeddings/
    mstar/
      cptac_brca/                                 # mSTAR slide embeddings (.h5)
      cptac_ucec/
  patch_features/
    mstar/
      cptac_brca/pt_files/                        # mSTAR patch features (.pt, intermediate)
      cptac_ucec/pt_files/
```

---

## License

This project is licensed under [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
Non-commercial, academic use only. Attribution required.

### Dependency licenses

This project depends on the following tools and models, each with their own license:

| Dependency | License | Notes |
|---|---|---|
| [TITAN](https://github.com/mahmoodlab/TITAN) | CC BY-NC-ND 4.0 | Non-commercial, no derivatives |
| [TRIDENT](https://github.com/mahmoodlab/TRIDENT) | CC BY-NC-ND 4.0 | Non-commercial, no derivatives |
| [mSTAR](https://github.com/Innse/mSTAR) | CC BY-NC-ND 4.0 | Non-commercial, no derivatives |
| [CLAM](https://github.com/mahmoodlab/CLAM) | GPLv3, non-commercial | Academic use only |
| [Patho-Bench](https://github.com/mahmoodlab/Patho-Bench) | CC BY-NC-ND 4.0 | Non-commercial, no derivatives |

Users must comply with each dependency's license independently.

---

## Citations

If you use this pipeline or its outputs, please cite the following:

**TITAN**
```bibtex
@article{ding2025multimodal,
  title={A multimodal whole-slide foundation model for pathology},
  author={Ding, Tong and Wagner, Sophia J and Song, Andrew H and Chen, Richard J and Lu, Ming Y and Zhang, Andrew and Vaidya, Anurag J and Jaume, Guillaume and Shaban, Muhammad and Kim, Ahrong and others},
  journal={Nature Medicine},
  volume={31},
  pages={3749--3761},
  year={2025},
  doi={10.1038/s41591-025-03982-3}
}
```

**mSTAR**
```bibtex
@article{xu2025mstar,
  title={A multimodal knowledge-enhanced whole-slide pathology foundation model},
  author={Xu, Yingxue and Wang, Yihui and Zhou, Fengtao and others},
  journal={Nature Communications},
  volume={16},
  number={11406},
  year={2025},
  doi={10.1038/s41467-025-66220-x}
}
```

**TRIDENT and Patho-Bench**
```bibtex
@article{zhang2025accelerating,
  title={Accelerating Data Processing and Benchmarking of AI Models for Pathology},
  author={Zhang, Andrew and Jaume, Guillaume and Vaidya, Anurag and Ding, Tong and Mahmood, Faisal},
  journal={arXiv preprint arXiv:2502.06750},
  year={2025}
}
```

**CLAM**
```bibtex
@article{lu2021data,
  title={Data-efficient and weakly supervised computational pathology on whole-slide images},
  author={Lu, Ming Y and Williamson, Drew F K and Chen, Tiffany Y and Chen, Richard J and Barbieri, Matteo and Mahmood, Faisal},
  journal={Nature Biomedical Engineering},
  volume={5},
  pages={555--570},
  year={2021},
  doi={10.1038/s41551-020-00682-w}
}
```

**CPTAC-BRCA**
```bibtex
@dataset{cptac_brca,
  author={National Cancer Institute Clinical Proteomic Tumor Analysis Consortium (CPTAC)},
  title={The Clinical Proteomic Tumor Analysis Consortium Breast Invasive Carcinoma Collection (CPTAC-BRCA)},
  year={2020},
  publisher={The Cancer Imaging Archive},
  doi={10.7937/TCIA.CAEM-YS80}
}
```

**CPTAC-UCEC**
```bibtex
@dataset{cptac_ucec,
  author={National Cancer Institute Clinical Proteomic Tumor Analysis Consortium (CPTAC)},
  title={The Clinical Proteomic Tumor Analysis Consortium Uterine Corpus Endometrial Carcinoma Collection (CPTAC-UCEC)},
  year={2018},
  publisher={The Cancer Imaging Archive},
  doi={10.7937/K9/TCIA.2018.3R3JUISW}
}
```

**TCIA**
```bibtex
@article{clark2013cancer,
  title={The Cancer Imaging Archive (TCIA): maintaining and operating a public information repository},
  author={Clark, Kenneth and Vendt, Bruce and Smith, Kirk and Freymann, John and Kirby, Justin and Koppel, Paul and Moore, Stephen and Phillips, Stanley and Maffitt, David and Pringle, Michael and Tarbox, Lawrence and Prior, Fred},
  journal={Journal of Digital Imaging},
  volume={26},
  number={6},
  pages={1045--1057},
  year={2013},
  doi={10.1007/s10278-013-9622-7}
}
```

**Required CPTAC acknowledgement statement** (for any publication using this data):

> Data used in this publication were generated by the National Cancer Institute Clinical Proteomic Tumor Analysis Consortium (CPTAC).

**AI Acknowledgement**

Claude (Anthropic, claude.ai) was used to assist with code development, documentation, and pipeline verification during this project.
