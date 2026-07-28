from pydantic import BaseModel, Field
from types import Literal, List, Optional

class DocumentPerson(BaseModel):

    ## anagraphic data
    local_id : str = Field(
        ..., 
        description="a unique local ID, exclusive of this JSON. It is used to define the relationships between the people (e.g. baby_01, father_01, witness_01...)"
    ), 

    name : Optional[str] = Field(
        None, 
        description="the first name of the person, exactly as reported in the document"
    )
    surname : Optional[str] = Field(
        None, 
        description="the last name of the person, exactly as reported in the document"
    )

    age : Optional[str] = Field(
        None, 
        description="the age of the person, expressed in years, if declared"
    )

    is_alive : Optional[bool] = Field(
        None, 
        description="True if introduced by \"di\" (like \"Marco Castiglioni di Giovanni\"), False if introduced by \"fu\"(like Marco Castiglioni, fu Giovanni)"

    )

    residence  : Optional[str] = Field(
        None, 
        description="place of birth or residence, if present in the text. in the format town, address"
    )

    role : Literal["newborn", "husband", "bride", "dead", "father", "mother", "witness", "officiant"]

    ## relationships

    father_id : Optional[str] = Field(
        None, 
        description= "the local_id of the father, if present"
    )
    mother_id : Optional[str] = Field(
        None, 
        description= "the local_id of the mother, if present"
    )
    
    spouse_id : Optional[str] = Field(
        None, 
        description= "the local_id of the spouse, if present"
    )

    class DocumentExtraction(BaseModel):
        document_type : Literal["Death_Certificate", "Birth_Certificate", "Marriage_Certificate"]
        document_date : Optional[str] = Field(
            None, 
            description="the date of the document, if present, in the format YYYY-MM-DD HH-mm"
        )