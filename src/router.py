# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

from fastapi import APIRouter

from .modules.complex_pairing.router import router as complex_pairing_router
from .modules.correlation.router import router as correlation_router
from .modules.extension_att.router import router as extension_router
from .modules.focus_type.router import router as focus_type_router
from .modules.mapping.router import router as mapping_router
from .modules.matching.router import router as matching_router
from .modules.object_type.router import router as object_type_router

root_router = APIRouter()

"""
Root API router that aggregates all sub-module routers under their respective prefixes and tags.
"""

# Include each endpoint router with a prefix and optional tags
root_router.include_router(object_type_router, prefix="/objectType", tags=["objectType"])
root_router.include_router(mapping_router, prefix="/mapping", tags=["mapping"])
root_router.include_router(matching_router, prefix="/matching", tags=["matching"])
root_router.include_router(focus_type_router, prefix="/focusType", tags=["focusType"])
root_router.include_router(complex_pairing_router, prefix="/complexPairing", tags=["complexPairing"])
root_router.include_router(extension_router, prefix="/extensionAttributes", tags=["extensionAttributes"])
root_router.include_router(correlation_router, prefix="/correlation", tags=["correlation"])
