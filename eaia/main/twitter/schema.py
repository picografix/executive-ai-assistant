import email
from typing import Annotated, List, Literal
from langchain_core.pydantic_v1 import BaseModel, Field
from langgraph.graph.message import AnyMessage
from typing_extensions import TypedDict


from langgraph.graph import add_messages

class TweetData(TypedDict):
    id: str
    tweet_handle: str
    tweet_content: str
    media: str
    send_time: str

class RespondTo(BaseModel):
    logic: str = Field(
        description="logic on WHY the response choice is the way it is", default=""
    )
    response: Literal["no", "email", "notify", "question"] = "no"

class ResponseTweetDraft(BaseModel):
    """Draft of an tweet to send as a response."""

    content: str
    tweet_handles: List[str]

class NewTweetDraft(BaseModel):
    """Draft of a new tweet to send."""

    content: str
    tweet_handles: List[str]
    
class ReWriteTweet(BaseModel):
    """Logic for rewriting an tweet"""
    tone_logic: str = Field(
        description="Logic for what the tone of the rewritten email should be"
    )
    rewritten_content: str = Field(description="Content rewritten with the new tone")



class Question(BaseModel):
    """Question to ask user."""

    content: str
    

class Ignore(BaseModel):
    """Call this to ignore the tweet. Only call this if user has said to do so."""

    ignore: bool

def convert_obj(o, m):
    if isinstance(m, dict):
        return RespondTo(**m)
    else:
        return m

class State(TypedDict):
    email: TweetData
    triage: Annotated[RespondTo, convert_obj]
    messages: Annotated[List[AnyMessage], add_messages]

tweet_template = """from: {tweet_handle}
To: {to_email}
{tweet_content}
"""
