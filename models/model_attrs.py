from typing import List, Optional
import attrs

@attrs.define
class EmbeddedEmote:
    id: str
    emoteID: str
    from_: int = attrs.field(metadata={'alias': 'from'})
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class CommentMessageFragment:
    emote: Optional[EmbeddedEmote]
    text: str
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class Badge:
    id: str
    setID: str
    version: str
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class CommentMessage:
    fragments: List[CommentMessageFragment]
    userBadges: List[Badge]
    userColor: Optional[str]
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class Commenter:
    id: str
    login: str
    displayName: str
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class Comment:
    id: str
    commenter: Optional[Commenter]
    contentOffsetSeconds: int
    createdAt: str
    message: CommentMessage
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class CommentEdge:
    cursor: str
    node: Comment
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class PageInfo:
    hasNextPage: bool
    hasPreviousPage: bool
    typename: str = attrs.field(metadata={'alias': '__typename'})

@attrs.define
class CommentsPage:
    edges: List[CommentEdge]
    pageInfo: PageInfo
    typename: str = attrs.field(metadata={'alias': '__typename'})

