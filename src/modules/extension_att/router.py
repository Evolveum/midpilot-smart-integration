# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from ...common.langfuse import ObservableAPIRouter
from . import service
from .schema import (
    SuggestExtensionRequest,
    SuggestExtensionResponse,
)

router = ObservableAPIRouter()


@router.post("/suggestExtensionAttributes", response_model=SuggestExtensionResponse)
async def suggest_extension_attributes(req: SuggestExtensionRequest):
    """
    Suggest extension attributes.
    """
    return await service.suggest_extension(req)
