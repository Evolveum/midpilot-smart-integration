# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi import APIRouter

from . import service
from .schema import ComplexPairingRequest, ComplexPairingResponse

router = APIRouter()


@router.post("/complexPairing", response_model=ComplexPairingResponse)
async def complex_pairing(req: ComplexPairingRequest):
    """
    Perform complex pairing matching across 5 samples.
    Returns similar=true if at least 3/5 are clear or near-matches.
    """
    return await service.complex_pairing(req)
