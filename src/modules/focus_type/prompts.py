# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from typing import List, Optional

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .schema import FocusType, SuggestFocusTypeResponse


class FocusTypePromptInput(BaseModel):
    """
    Input model for focus type classification prompt.
    """

    object_class: str = Field(..., alias="objectClass", description="The object class being analyzed")
    kind: str = Field(..., description="The kind of object")
    intent: str = Field(..., description="The intent or purpose of the analysis")
    attributes: List[str] = Field(..., description="List of attribute names")
    delineation: Optional[str] = Field(None, description="Optional delineation information")


FOCUS_TYPE_NAMES = [t.value for t in FocusType]

suggest_focus_type_system_prompt = f"""
## System Prompt

You are an Identity Governance Assistant. Your task is to classify each incoming item into one of these focus types: {", ".join(FOCUS_TYPE_NAMES)}.

**IMPORTANT GUIDELINES:**

### 1. INPUT STRUCTURE
You will receive a JSON object with the following structure:
- objectClass (string): The object class being analyzed
- kind (string): The kind of object
- intent (string): The intent or purpose of the analysis
- attributes (array): List of attribute names
- delineation (string, optional): Optional delineation information

### 2. FOCUS TYPE DEFINITIONS
- **User**: A single human or service account. Physical person–like properties.
- **Role**: Access-control grouping defining privileges (e.g., Admin, Reader).
- **Organization**: Hierarchical or group unit (e.g., Department, Team, OU).
- **Service**: Concrete or abstract services/devices (e.g., VM, printer, application).

### 3. OUTPUT FORMAT
IMPORTANT:
Return a valid JSON object matching this schema:

```json
{{{{
  "focusTypeName": "UserType|RoleType|OrgType|ServiceType"
}}}}
```""".strip()

suggest_focus_type_human_prompt = """
Here is the JSON item:
```json
{payload_json}
```
""".strip()


parser: PydanticOutputParser = PydanticOutputParser(pydantic_object=SuggestFocusTypeResponse)
