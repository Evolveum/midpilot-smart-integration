# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from ...common.langfuse import ObservableAPIRouter
from . import service
from .schema import (
    SuggestFocusTypeRequest,
    SuggestFocusTypeResponse,
)

router = ObservableAPIRouter()


@router.post("/suggestFocusType", response_model=SuggestFocusTypeResponse)
async def suggest_focus_type(req: SuggestFocusTypeRequest):
    """
    Suggest focus type for an object type and application schema.
    """
    return await service.suggest_focus_type(req)
