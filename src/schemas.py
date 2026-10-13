from typing import Literal, List, Optional
from pydantic import BaseModel, Field


class DocumentPerson(BaseModel):
    # anagraphic data
    local_id: str = Field(
        ...,
        description="a unique local ID, exclusive of this JSON. It is used to define the relationships between the people (e.g. baby_01, father_01, witness_01...)"
    )

    # nome = first name
    name: Optional[str] = Field(
        None,
        description="the first name (nome) of the person, exactly as reported in the document"
    )
    # cognome = last name
    surname: Optional[str] = Field(
        None,
        description="the last name (cognome) of the person, exactly as reported in the document"
    )

    gender: Optional[Literal["male", "female"]] = Field(
        None, 
        description = "the sex/gender of the person, if indicated in the document"
    )

    age: Optional[str] = Field(
        None,
        description="the age of the person, expressed in years, if declared"
    )

    birth_date: Optional[str] = Field(
        None,
        description="the date of birth of the individual, if present, in the format YYYY-MM-DD"
    )

    death_date: Optional[str] = Field(
    None,
    description="the date of death of the individual, if present, in the format YYYY-MM-DD"
    )

    # "di" = son/daughter of (living parent), "fu" = the late (deceased)
    is_alive: Optional[bool] = Field(
        None,
        description='True if introduced by "di" (e.g. "Marco Castiglioni di Giovanni"), False if introduced by "fu" (e.g. "Marco Castiglioni, fu Giovanni")'
    )

    birthplace: Optional[str] = Field(
        None, 
        description="place of birth of the individual, if present in the text, in the format town, address"
    )

    residence: Optional[str] = Field(
        None,
        description="place of residence of the individual, if present in the text, in the format town, address"
    )

    # contadino = farmer, sarto = tailor; values are kept in Italian as written
    profession : Optional[str] = Field(
        None, 
        description= "The profession of the person, if present in the document, like contadino, sarto, etc"
    )

    role: Literal[
        "newborn", "husband", "bride", "dead",
        "father", "mother", "witness", "officiant", "spouse_of_the_deceased"
    ] = Field(
        ...,
        description="the role this person plays in the document. father/mother refer to the parents of the newborn (birth certs) or of a spouse (marriage certs), depending on document_type"
    )

    # relationships
    father_id: Optional[str] = Field(
        None,
        description="the local_id of the father, if present"
    )
    mother_id: Optional[str] = Field(
        None,
        description="the local_id of the mother, if present"
    )
    spouse_id: Optional[str] = Field(
        None,
        description="the local_id of the spouse, if present"
    )


class DocumentExtraction(BaseModel):
    document_type: Literal[
        "Death_Certificate", "Birth_Certificate", "Marriage_Certificate", "Marriage_Banns"
    ]
    document_date: Optional[str] = Field(
        None,
        description="the date of the document, if present, in the format YYYY-MM-DD"
    )

    people_present: List[DocumentPerson] = Field(
        default_factory=list,
        description="complete list of all human entities present in the document"
    )