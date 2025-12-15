# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from ...common.langfuse import ObservableAPIRouter
from . import service
from .schema import MatchSchemaRequest, MatchSchemaResponse

router = ObservableAPIRouter()


@router.post("/matchSchema", response_model=MatchSchemaResponse)
async def match_midpoint_schema(req: MatchSchemaRequest):
    """
    Matches attributes of two schemas providing multiple suggestions per attribute.
    """
    return await service.match_midpoint_schema(req)
