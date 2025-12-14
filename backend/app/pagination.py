"""
Waiting The Longest™ - Pagination Utilities
=============================================
Reusable pagination for database queries and API responses.
"""

from dataclasses import dataclass
from typing import TypeVar, Generic, Sequence, Any
from urllib.parse import urlencode, urlparse, parse_qs

from pydantic import BaseModel, Field


T = TypeVar("T")


# =============================================================================
# Pagination Parameters
# =============================================================================

@dataclass
class PaginationParams:
    """Parameters for pagination."""
    
    page: int = 1
    page_size: int = 20
    
    # Limits
    MIN_PAGE_SIZE: int = 1
    MAX_PAGE_SIZE: int = 100
    DEFAULT_PAGE_SIZE: int = 20
    
    def __post_init__(self):
        """Validate and normalize pagination params."""
        self.page = max(1, self.page)
        self.page_size = max(
            self.MIN_PAGE_SIZE,
            min(self.page_size, self.MAX_PAGE_SIZE)
        )
    
    @property
    def offset(self) -> int:
        """Calculate offset for SQL queries."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Alias for page_size."""
        return self.page_size
    
    @classmethod
    def from_request(cls, page: int | None = None, page_size: int | None = None) -> "PaginationParams":
        """Create pagination params from request parameters."""
        return cls(
            page=page or 1,
            page_size=page_size or cls.DEFAULT_PAGE_SIZE,
        )


# =============================================================================
# Paginated Response
# =============================================================================

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response model."""
    
    items: list[T] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")
    
    class Config:
        arbitrary_types_allowed = True


# =============================================================================
# Page Info
# =============================================================================

@dataclass
class PageInfo:
    """Information about a paginated result set."""
    
    total: int
    page: int
    page_size: int
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.total_pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1
    
    @property
    def first_item(self) -> int:
        """Get the index of the first item on this page (1-based)."""
        if self.total == 0:
            return 0
        return (self.page - 1) * self.page_size + 1
    
    @property
    def last_item(self) -> int:
        """Get the index of the last item on this page (1-based)."""
        return min(self.page * self.page_size, self.total)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_prev": self.has_prev,
        }


# =============================================================================
# Paginator
# =============================================================================

class Paginator(Generic[T]):
    """
    Generic paginator for sequences.
    """
    
    def __init__(
        self,
        items: Sequence[T],
        page: int = 1,
        page_size: int = 20,
    ):
        self.items = items
        self.params = PaginationParams(page=page, page_size=page_size)
    
    @property
    def total(self) -> int:
        """Total number of items."""
        return len(self.items)
    
    @property
    def page_info(self) -> PageInfo:
        """Get page information."""
        return PageInfo(
            total=self.total,
            page=self.params.page,
            page_size=self.params.page_size,
        )
    
    def get_page(self) -> list[T]:
        """Get items for current page."""
        start = self.params.offset
        end = start + self.params.page_size
        return list(self.items[start:end])
    
    def paginate(self) -> dict[str, Any]:
        """Get paginated response as dictionary."""
        return {
            "items": self.get_page(),
            **self.page_info.to_dict(),
        }


# =============================================================================
# Cursor Pagination
# =============================================================================

@dataclass
class CursorPaginationParams:
    """Parameters for cursor-based pagination."""
    
    cursor: str | None = None
    limit: int = 20
    
    MAX_LIMIT: int = 100
    
    def __post_init__(self):
        """Validate params."""
        self.limit = min(max(1, self.limit), self.MAX_LIMIT)


@dataclass
class CursorPage(Generic[T]):
    """Result of cursor-based pagination."""
    
    items: list[T]
    next_cursor: str | None
    has_more: bool
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "items": self.items,
            "next_cursor": self.next_cursor,
            "has_more": self.has_more,
        }


class CursorPaginator(Generic[T]):
    """
    Cursor-based pagination for large datasets.
    Uses the last item's ID as the cursor.
    """
    
    def __init__(
        self,
        items: Sequence[T],
        cursor: str | None = None,
        limit: int = 20,
        id_field: str = "id",
    ):
        self.items = items
        self.params = CursorPaginationParams(cursor=cursor, limit=limit)
        self.id_field = id_field
    
    def get_page(self) -> CursorPage[T]:
        """Get items for current cursor position."""
        start_idx = 0
        
        # Find starting position if cursor provided
        if self.params.cursor:
            for i, item in enumerate(self.items):
                item_id = getattr(item, self.id_field, None) or item.get(self.id_field)
                if str(item_id) == self.params.cursor:
                    start_idx = i + 1
                    break
        
        # Get items
        end_idx = start_idx + self.params.limit
        page_items = list(self.items[start_idx:end_idx])
        has_more = end_idx < len(self.items)
        
        # Get next cursor
        next_cursor = None
        if page_items and has_more:
            last_item = page_items[-1]
            next_cursor = str(
                getattr(last_item, self.id_field, None) or 
                last_item.get(self.id_field)
            )
        
        return CursorPage(
            items=page_items,
            next_cursor=next_cursor,
            has_more=has_more,
        )


# =============================================================================
# Link Header Builder
# =============================================================================

class LinkHeaderBuilder:
    """
    Builds RFC 5988 Link headers for pagination.
    """
    
    def __init__(self, base_url: str, page_info: PageInfo):
        self.base_url = base_url
        self.page_info = page_info
    
    def build(self) -> str:
        """Build the Link header value."""
        links = []
        
        # Parse existing URL
        parsed = urlparse(self.base_url)
        params = parse_qs(parsed.query)
        
        def make_link(page: int, rel: str) -> str:
            params["page"] = [str(page)]
            query = urlencode(params, doseq=True)
            url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{query}"
            return f'<{url}>; rel="{rel}"'
        
        # First page
        links.append(make_link(1, "first"))
        
        # Previous page
        if self.page_info.has_prev:
            links.append(make_link(self.page_info.page - 1, "prev"))
        
        # Next page
        if self.page_info.has_next:
            links.append(make_link(self.page_info.page + 1, "next"))
        
        # Last page
        if self.page_info.total_pages > 0:
            links.append(make_link(self.page_info.total_pages, "last"))
        
        return ", ".join(links)


# =============================================================================
# SQLAlchemy Pagination Helper
# =============================================================================

def paginate_query(
    query: Any,  # SQLAlchemy Query
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Any], PageInfo]:
    """
    Paginate a SQLAlchemy query.
    
    Returns:
        Tuple of (items, page_info)
    """
    params = PaginationParams(page=page, page_size=page_size)
    
    # Get total count
    total = query.count()
    
    # Get items for page
    items = query.offset(params.offset).limit(params.limit).all()
    
    # Create page info
    page_info = PageInfo(
        total=total,
        page=params.page,
        page_size=params.page_size,
    )
    
    return items, page_info
