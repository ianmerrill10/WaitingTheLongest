"""
===============================================================================
Waiting The Longest™ - API Versioning Support
===============================================================================
Purpose: Support multiple API versions for backward compatibility.
         Allows gradual migration to new API versions.

Author: Waiting The Longest™ Development Team
===============================================================================
"""

import re
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.routing import APIRoute


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    V2 = "v2"
    LATEST = "v2"  # Alias for latest version


def get_version_from_header(
    accept: str = Header(default="application/json")
) -> APIVersion:
    """
    Extract API version from Accept header.
    
    Supports:
    - application/vnd.wtl.v1+json
    - application/vnd.wtl.v2+json
    - application/json (defaults to latest)
    """
    # Check for versioned media type
    match = re.search(r"application/vnd\.wtl\.(v\d+)\+json", accept)
    if match:
        version_str = match.group(1)
        try:
            return APIVersion(version_str)
        except ValueError:
            pass
    
    # Default to latest
    return APIVersion.LATEST


def get_version_from_path(path: str) -> Optional[APIVersion]:
    """
    Extract API version from URL path.
    
    Supports:
    - /api/v1/animals
    - /api/v2/animals
    """
    match = re.search(r"/api/(v\d+)/", path)
    if match:
        version_str = match.group(1)
        try:
            return APIVersion(version_str)
        except ValueError:
            pass
    return None


class VersionedAPIRouter(APIRouter):
    """
    Router that supports multiple API versions.
    
    Usage:
        router = VersionedAPIRouter(prefix="/api")
        
        @router.get("/animals", versions=[APIVersion.V1, APIVersion.V2])
        async def get_animals():
            ...
        
        @router.get("/animals", versions=[APIVersion.V2])
        async def get_animals_v2():
            # V2-only implementation
            ...
    """
    
    def __init__(self, *args, **kwargs):
        self.default_version = kwargs.pop("default_version", APIVersion.LATEST)
        super().__init__(*args, **kwargs)
        self._version_routes: Dict[str, Dict[APIVersion, Callable]] = {}
    
    def api_route(
        self,
        path: str,
        *args,
        versions: Optional[List[APIVersion]] = None,
        **kwargs
    ) -> Callable:
        """
        Register a route with version support.
        
        Args:
            path: Route path
            versions: List of supported versions (None means all versions)
            **kwargs: Additional route kwargs
        """
        versions = versions or list(APIVersion)
        
        def decorator(func: Callable) -> Callable:
            for version in versions:
                versioned_path = f"/{version.value}{path}"
                
                @wraps(func)
                async def versioned_handler(*a, **kw):
                    return await func(*a, **kw)
                
                super(VersionedAPIRouter, self).api_route(
                    versioned_path, *args, **kwargs
                )(versioned_handler)
            
            return func
        
        return decorator
    
    def get(self, path: str, *args, versions: Optional[List[APIVersion]] = None, **kwargs):
        """GET route with version support."""
        return self.api_route(path, *args, versions=versions, methods=["GET"], **kwargs)
    
    def post(self, path: str, *args, versions: Optional[List[APIVersion]] = None, **kwargs):
        """POST route with version support."""
        return self.api_route(path, *args, versions=versions, methods=["POST"], **kwargs)
    
    def put(self, path: str, *args, versions: Optional[List[APIVersion]] = None, **kwargs):
        """PUT route with version support."""
        return self.api_route(path, *args, versions=versions, methods=["PUT"], **kwargs)
    
    def delete(self, path: str, *args, versions: Optional[List[APIVersion]] = None, **kwargs):
        """DELETE route with version support."""
        return self.api_route(path, *args, versions=versions, methods=["DELETE"], **kwargs)
    
    def patch(self, path: str, *args, versions: Optional[List[APIVersion]] = None, **kwargs):
        """PATCH route with version support."""
        return self.api_route(path, *args, versions=versions, methods=["PATCH"], **kwargs)


def deprecated(
    since_version: APIVersion,
    removal_version: Optional[APIVersion] = None,
    alternative: Optional[str] = None
) -> Callable:
    """
    Mark an endpoint as deprecated.
    
    Adds deprecation headers to response.
    
    Args:
        since_version: Version when deprecation started
        removal_version: Version when endpoint will be removed
        alternative: Alternative endpoint to use
    
    Usage:
        @router.get("/old-endpoint")
        @deprecated(since_version=APIVersion.V2, alternative="/new-endpoint")
        async def old_endpoint():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from fastapi import Response
            
            # Find Response in args if passed
            response = None
            for arg in args:
                if isinstance(arg, Response):
                    response = arg
                    break
            
            result = await func(*args, **kwargs)
            
            # Build deprecation message
            msg_parts = [f"Deprecated since {since_version.value}"]
            if removal_version:
                msg_parts.append(f"will be removed in {removal_version.value}")
            if alternative:
                msg_parts.append(f"use {alternative} instead")
            
            # Add to response headers if available
            if hasattr(result, "headers"):
                result.headers["Deprecation"] = "; ".join(msg_parts)
                result.headers["Sunset"] = removal_version.value if removal_version else "TBD"
            
            return result
        
        # Mark function as deprecated for docs
        wrapper.__doc__ = f"**DEPRECATED**: {func.__doc__ or ''}\n\n{'; '.join([])}"
        
        return wrapper
    return decorator


def version_specific(
    v1_handler: Optional[Callable] = None,
    v2_handler: Optional[Callable] = None
) -> Callable:
    """
    Create a handler that calls different functions based on version.
    
    Usage:
        @router.get("/data")
        @version_specific(v1_handler=get_data_v1, v2_handler=get_data_v2)
        async def get_data(request: Request):
            pass  # Never called, version_specific handles dispatch
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Get version from path
            version = get_version_from_path(str(request.url.path))
            
            # Fall back to header
            if version is None:
                accept = request.headers.get("Accept", "application/json")
                version = get_version_from_header(accept)
            
            # Dispatch to version-specific handler
            if version == APIVersion.V1 and v1_handler:
                return await v1_handler(request, *args, **kwargs)
            elif version == APIVersion.V2 and v2_handler:
                return await v2_handler(request, *args, **kwargs)
            elif v2_handler:
                return await v2_handler(request, *args, **kwargs)
            elif v1_handler:
                return await v1_handler(request, *args, **kwargs)
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"No handler for API version {version.value}"
                )
        
        return wrapper
    return decorator


# Response model versions for different API versions
class ResponseVersion:
    """
    Helper for managing response model versions.
    
    Usage:
        class AnimalV1(BaseModel):
            id: int
            name: str
        
        class AnimalV2(AnimalV1):
            days_waiting: int
            shelter_name: str
        
        responses = ResponseVersion()
        responses.register(APIVersion.V1, AnimalV1)
        responses.register(APIVersion.V2, AnimalV2)
        
        # Get model for version
        model = responses.get(APIVersion.V2)  # AnimalV2
    """
    
    def __init__(self):
        self._models: Dict[APIVersion, Type] = {}
    
    def register(self, version: APIVersion, model: Type) -> None:
        """Register a model for a version."""
        self._models[version] = model
    
    def get(self, version: APIVersion) -> Optional[Type]:
        """Get model for version."""
        return self._models.get(version)
    
    def latest(self) -> Optional[Type]:
        """Get model for latest version."""
        return self._models.get(APIVersion.LATEST)
