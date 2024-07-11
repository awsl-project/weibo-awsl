from typing import List, Optional
from pydantic import BaseModel


class WeiboListItem(BaseModel):
    id: int
    mblogid: str
    text_raw: str
    user: Optional[dict] = None
    retweeted_status: Optional["WeiboListItem"] = None


class WeiboListData(BaseModel):
    list: Optional[List[WeiboListItem]] = None


class WeiboList(BaseModel):
    data: Optional[WeiboListData] = None
