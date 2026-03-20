# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from ...common.langfuse import ObservableAPIRouter
from . import service
from .schema import SuggestCategoricalMappingRequest, SuggestCategoricalMappingResponse

router = ObservableAPIRouter()


@router.post("/suggestCategoricalMapping", response_model=SuggestCategoricalMappingResponse)
async def suggest_categorical_mapping_script(req: SuggestCategoricalMappingRequest):
    """
    Suggest a Groovy value-mapping script for a categorical (enum-valued) attribute.
    Uses value distribution and known midPoint enum values instead of data pairs.
    """
    return await service.suggest_categorical_mapping_script(req)
