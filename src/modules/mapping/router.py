# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from ...common.langfuse import ObservableAPIRouter
from . import service
from .schema import (
    SuggestMappingRequest,
    SuggestMappingResponse,
)

router = ObservableAPIRouter()


@router.post("/suggestMapping", response_model=SuggestMappingResponse)
async def suggest_mapping_script(req: SuggestMappingRequest):
    """
    Suggest mapping script or complex attribute.
    """
    return await service.suggest_mapping_script(req)
