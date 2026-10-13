# maiores

Automated ELT pipeline for historical demographics. Extracts entities from raw documents via VLM, performs automated resolution, and builds population graphs in Neo4j.


In our specific application, we have focused on the Italian civil registry records (births, marriages, marriage banns, deaths) from 1866 onwards.

## Pipeline

| Stage | Module | Status |
| --- | --- | --- |
| Crop raw scans | `src/cropper.py` | not started |
| Extract people and relationships | `src/extractor.py` | working prototype |
| Batch loading | `src/batch_loader.py` | not started |
| Orchestration | `src/orchestrator.py` | not started |
| Failed documents (dead letter queue) | `src/dlq.py` | not started |
| Load into Neo4j | `src/graph_loader.py` | not started |

### Extraction

`process_document(image_path)` runs three steps:

1. **Transcription**: the image is sent to Gemini (`gemini-3.1-flash-lite`), which returns a faithful transcription. Uncertain words are marked with `[?]`.
2. **Structuring**: the transcription is turned into JSON that follows the `DocumentExtraction` schema in `src/schemas.py`.
3. **Consistency rules**: `enforce_consistency` makes the result coherent. It makes spouse links symmetric and infers roles from relationships. It also infers `is_alive` and `gender` from roles.

`save_extraction` writes the result, the transcription and some metadata to `data/2-processed/<image>__<tag>.json`.

After some experimentation, it has been shown that the separation and specialization of the single models in steps (to extract first the text and then generate the structured output) helps to reduce errors, even with a less expensive model. We hypothesize that is due to a reduction of the model mental load and to a more precise prompt. 

We also have used a deterministic enforcer in order to reduce the errors and problems in the extraction process

### Data model

- `DocumentExtraction` holds the document type, the document date and the list of people.
- `DocumentPerson` holds the personal data, the person's role in the document, and `father_id` / `mother_id` / `spouse_id`. These IDs point to the `local_id` of other people in the same document.

## Setup

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Create a `.env` file in the project root with your Gemini API key:

```text
GOOGLE_API_KEY=...
```

## Usage

```python
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append("src")

from extractor import process_document, save_extraction

image_path = "data/1-cropped/test_image_01.jpg"
result, transcription = process_document(image_path)
save_extraction(result, image_path, transcription=transcription, tag="my_experiment")
```

Run this from the project root.

## Data layout

`data/` and the notebooks are not versioned (see `.gitignore`). The expected layout is:

```text
data/
├── 0-raw/            # original scans, one folder per record type and period
├── 0-ground_truth/   # hand-annotated extractions (<image>__gt.json)
├── 1-cropped/        # cropped document images
├── 2-processed/      # extraction outputs (<image>__<tag>.json)
└── 3-failed/         # documents that could not be processed
```

Experiments are compared against `0-ground_truth/`. Each output is tagged with the prompt or method version that produced it, for example `prompt_v3` or `consistency_check_v2`.
