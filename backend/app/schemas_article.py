from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ArticleBase(BaseModel):
    title: str
    category: str
    content: str
    read_time: Optional[str] = "5 min read"
    is_published: Optional[bool] = True

class ArticleCreate(ArticleBase):
    slug: str

class ArticleResponse(ArticleBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    views: int

    class Config:
        from_attributes = True

class ArticleListResponse(BaseModel):
    items: List[ArticleResponse]
    total: int
