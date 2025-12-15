# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from ...common.langfuse import ObservableAPIRouter
from . import service
from .schema import (
    SuggestObjectTypeRequest,
    SuggestObjectTypeResponse,
)

router = ObservableAPIRouter()


@router.post("/suggestObjectType", response_model=SuggestObjectTypeResponse, response_model_exclude_none=True)
async def suggest_delineation(req: SuggestObjectTypeRequest):
    """
    Suggest midPoint object types (kind, intent and delineations) for the given object class.
    """
    return await service.suggest_delineation(req)
