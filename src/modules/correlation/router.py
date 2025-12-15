# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from ...common.langfuse import ObservableAPIRouter
from . import service
from .schema import (
    SuggestExtensionCorrelatorsRequest,
    SuggestExtensionCorrelatorsResponse,
)

router = ObservableAPIRouter()


@router.post("/suggestExtensionCorrelators", response_model=SuggestExtensionCorrelatorsResponse)
async def suggest_extension_correlators(req: SuggestExtensionCorrelatorsRequest):
    """
    Suggest suitable correlators based on provided extension attributes.
    """
    return await service.suggest_extension_correlators(req)
