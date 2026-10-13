import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from google import genai
from schemas import DocumentExtraction

MODEL_NAME = "gemini-3.1-flash-lite"

# The prompts quote Italian terms from the documents on purpose, so the model can recognise them:
# "di" = son/daughter of (parent alive), "fu" = the late (parent deceased),
# "figlio di" = son of, "residente in" = resident in, "millenovecento ventinove" = 1929.
TRANSCRIPTION_PROMPT = """
You are an expert in Italian paleography. Transcribe this historical Italian civil
registry document as faithfully as possible, preserving the original wording, 
including all names, ages, dates, places, professions, and relational phrases
(e.g. "di", "fu", "figlio di", "residente in"). Do not summarize, correct, or
interpret — just transcribe exactly what is written, including uncertain or
partially legible words marked with [?].

ATTENTION
- Always indicate the birth, marriage or death date of the main people, if present
- In the Fascist period (1927-1943) often are present TWO year markers next
to each other at the top of the act: the Gregorian year written in words (e.g.
"millenovecento ventinove") AND a small Roman numeral (e.g. "VII") indicating the
Fascist Era year 
"""

# The Cuorgnè example is a death record: Giovanni Battista Luigi Corippolo, 64, farmer,
# son of the late Giacomo (farmer) and the late Anna Fornengo (housewife, "casalinga").
STRUCTURE_PROMPT = """
You are an expert in Italian paleography and civil registry archives. You will
receive a transcription of a historical Italian civil registry document (birth,
marriage, marriage banns, or death certificate). Extract all people mentioned and
their relationships, following exactly the provided schema.

Important rules:
- Report first name and surname exactly as written in the transcription, without correcting or normalizing them.
- If information is not present or legible, leave the field null: do not invent data.
- Pay attention to "di" (living person) vs "fu" (deceased person) for the is_alive field.
- Every person must have a unique local_id that correctly links them to others via
  father_id, mother_id, spouse_id.

IMPORTANT - completeness of data for EVERY person:
Extract complete anagraphic data (age, birth place, residence, profession if present)
for EVERY person mentioned in the document, not just the main subject of the act.
This explicitly includes parents (father and mother) of spouses/newborns, and witnesses.

Example:
Transcription snippet: "...è morto Corippolo Giovanni Battista Luigi di anni
sessantaquattro, agricoltore, residente in Cuorgnè, nato in Cuorgnè, da fu Giacomo,
già contadino domiciliato in Cuorgnè, e dalla fu Fornengo Anna, già casalinga,
domiciliata in Cuorgnè..."
Expected extraction for the father: name="Giacomo", is_alive=false (introduced by "fu"),
residence="Cuorgnè", profession="contadino".
Expected extraction for the mother: name="Anna", surname="Fornengo", is_alive=false
(introduced by "fu"), residence="Cuorgnè", profession="casalinga".
"""


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def _guess_mime_type(image_path: str) -> str:
    ext = Path(image_path).suffix.lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    if ext not in mapping:
        raise ValueError(f"Unsupported image extension: {ext}")
    return mapping[ext]

def transcribe_document(image_path: str, model_name: str = MODEL_NAME) -> str:
    image_b64 = encode_image(image_path)
    mime_type = _guess_mime_type(image_path)

    client = genai.Client()

    response = client.models.generate_content(
        model=model_name,
        contents=[
            {"inline_data": {"mime_type": mime_type, "data": image_b64}},
            TRANSCRIPTION_PROMPT,
        ],
    )

    return response.text


def extract_structure_from_transcription(transcription: str, model_name:str = MODEL_NAME):
    client = genai.Client()

    response = client.models.generate_content(
        model = model_name, 
        contents = [
            f"Below you can find the transcription of an italian historical document:\n\n{transcription}",
            STRUCTURE_PROMPT,

        ],
        config={
            "response_mime_type" : "application/json", 
            "response_schema" : DocumentExtraction,
        },
    )
    
    return DocumentExtraction.model_validate_json(response.text)

def enforce_consistency(result: DocumentExtraction) -> DocumentExtraction:

    people_by_id = {p.local_id: p for p in result.people_present}

    # enforce symmetry in relationships

    for person in result.people_present:
        if person.spouse_id and person.spouse_id in people_by_id:
            partner = people_by_id[person.spouse_id]
            if not partner.spouse_id:
                partner.spouse_id = person.local_id
    
    # modify role based on relationship

    for person in result.people_present:
        if person.father_id and person.father_id in people_by_id:
            people_by_id[person.father_id].role = "father"
        if person.mother_id and person.mother_id in people_by_id:
            people_by_id[person.mother_id].role = "mother"
        if person.spouse_id and person.spouse_id in people_by_id:
            partner = people_by_id[person.spouse_id]
            if person.role == "dead" and partner.role not in ("husband", "bride", "father", "mother"):
                partner.role = "spouse_of_the_deceased"

    # modify is_alive status based on role

    for person in result.people_present:
        if person.role == "dead":
            person.is_alive = False
        elif person.role in ("witness", "officiant"):
            person.is_alive = True
        elif person.role in ("husband", "bride") and result.document_type in ("Marriage_Certificate", "Marriage_Banns"):
            person.is_alive = True

    # enforce gender in case of specific roles

    for person in result.people_present:
        if person.role in ("father", "husband"):
            person.gender = "male"
        if person.role in ("mother", "bride"):
            person.gender = "female"

    return result

def process_document(image_path:str, model_name:str = MODEL_NAME) -> tuple[DocumentExtraction, str]:
    transcription = transcribe_document(image_path, model_name)
    result = extract_structure_from_transcription(transcription, model_name)
    result = enforce_consistency(result)
    return result, transcription



def save_extraction(
    result: DocumentExtraction,
    image_path: str,
    output_dir: str = "data/2-processed",
    transcription: str | None = None,
    tag: str | None = None,
    model_name: str = MODEL_NAME,
    ) -> str:

    image_name = Path(image_path).stem
    filename = f"{image_name}__{tag}.json" if tag else f"{image_name}.json"
    output_path = Path(output_dir) / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "source_image": str(image_path),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "transcription" : transcription,
        "extraction": json.loads(result.model_dump_json()),
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(output_path)