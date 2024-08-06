
from typing import List, Optional
from pydantic import BaseModel, Field

class EmbeddedEmote(BaseModel):
    id: str
    emoteID: str
    from_: int = Field(alias='from')
    typename: str = Field(alias='__typename')

class CommentMessageFragment(BaseModel):
    emote: Optional[EmbeddedEmote]
    text: str
    typename: str = Field(alias='__typename')

class Badge(BaseModel):
    id: str
    setID: str
    version: str
    typename: str = Field(alias='__typename')

class CommentMessage(BaseModel):
    fragments: List[CommentMessageFragment]
    userBadges: List[Badge]
    userColor: Optional[str]
    typename: str = Field(alias='__typename')

class Commenter(BaseModel):
    id: str
    login: str
    displayName: str
    typename: str = Field(alias='__typename')

class Comment(BaseModel):
    id: str
    commenter: Optional[Commenter]
    contentOffsetSeconds: int
    createdAt: str
    message: CommentMessage
    typename: str = Field(alias='__typename')

class CommentEdge(BaseModel):
    cursor: str
    node: Comment
    typename: str = Field(alias='__typename')

class PageInfo(BaseModel):
    hasNextPage: bool
    hasPreviousPage: bool
    typename: str = Field(alias='__typename')

class CommentsPage(BaseModel):
    edges: List[CommentEdge]
    pageInfo: PageInfo
    typename: str = Field(alias='__typename')

