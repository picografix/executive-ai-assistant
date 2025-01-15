import json
from typing import TypedDict, Literal
from langgraph.graph import END, StateGraph
from langchain_core.messages import HumanMessage, ToolMessage
from eaia.main.config import get_config
from eaia.main.twitter.tweet import send_tweet
from eaia.main.twitter.schema import State
from eaia.main.twitter.triage import triage_input



def route_after_triage(
    state: State,
) -> Literal["draft_response", "mark_as_read_node", "notify"]:
    if state["triage"].response == "tweet":
        return "draft_response"
    elif state["triage"].response == "no":
        return "mark_as_read_node"
    elif state["triage"].response == "notify":
        return "notify"
    elif state["triage"].response == "question":
        return "draft_response"
    else:
        raise ValueError
    
def take_action(
    state: State,
) -> Literal[
    "send_message",
    "rewrite",
    "mark_as_read_node",
    "bad_tool_name",
]:
    prediction = state["messages"][-1]
    if len(prediction.tool_calls) != 1:
        raise ValueError
    tool_call = prediction.tool_calls[0]
    if tool_call["name"] == "Question":
        return "send_message"
    elif tool_call["name"] == "ResponseEmailDraft":
        return "rewrite"
    elif tool_call["name"] == "Ignore":
        return "mark_as_read_node"
    else:
        return "bad_tool_name"
    

def bad_tool_name(state: State):
    tool_call = state["messages"][-1].tool_calls[0]
    message = f"Could not find tool with name `{tool_call['name']}`. Make sure you are calling one of the allowed tools!"
    last_message = state["messages"][-1]
    last_message.tool_calls[0]["name"] = last_message.tool_calls[0]["name"].replace(
        ":", ""
    )
    return {
        "messages": [
            last_message,
            ToolMessage(content=message, tool_call_id=tool_call["id"]),
        ]
    }

def enter_after_human(
    state,
) -> Literal[
    "mark_as_read_node", "draft_response", "send_tweet_node"
]:
    messages = state.get("messages") or []
    if len(messages) == 0:
        if state["triage"].response == "notify":
            return "mark_as_read_node"
        raise ValueError
    else:
        if isinstance(messages[-1], (ToolMessage, HumanMessage)):
            return "draft_response"
        else:
            execute = messages[-1].tool_calls[0]
            if execute["name"] == "ResponseEmailDraft":
                return "send_tweet_node"
            elif execute["name"] == "Ignore":
                return "mark_as_read_node"
            elif execute["name"] == "Question":
                return "draft_response"
            else:
                raise ValueError
            
def send_tweet_node(state: State, config):
    tool_call = state["messages"][-1].tool_calls[0]
    _args = tool_call["args"]
    email = get_config(config)["tweet"]
    new_receipients = _args["new_recipients"]
    if isinstance(new_receipients, str):
        new_receipients = json.loads(new_receipients)
    send_tweet(
        state["tweet"]["id"],
        _args["content"],
        email,
        addn_receipients=new_receipients
    )
    
def mark_as_read_node(state):
    pass

def human_node(state: State):
    pass

class ConfigSchema(TypedDict):
    db_id: int
    model: str

graph_builder = StateGraph(State, config_schema=ConfigSchema)
graph_builder.add_node(human_node)
graph_builder.add_node(triage_input)
graph_builder.add_node(draft_response)
graph_builder.add_node(send_message)
graph_builder.add_node(rewrite)
graph_builder.add_node(mark_as_read_node)
graph_builder.add_node(send_email_draft)
graph_builder.add_node(send_email_node)
graph_builder.add_node(bad_tool_name)
graph_builder.add_node(notify)
graph_builder.add_node(send_cal_invite_node)
graph_builder.add_node(send_cal_invite)
graph_builder.add_conditional_edges("triage_input", route_after_triage)
graph_builder.set_entry_point("triage_input")
graph_builder.add_conditional_edges("draft_response", take_action)
graph_builder.add_edge("send_message", "human_node")
graph_builder.add_edge("send_cal_invite", "human_node")
graph_builder.add_node(find_meeting_time)
graph_builder.add_edge("find_meeting_time", "draft_response")
graph_builder.add_edge("bad_tool_name", "draft_response")
graph_builder.add_edge("send_cal_invite_node", "draft_response")
graph_builder.add_edge("send_email_node", "mark_as_read_node")
graph_builder.add_edge("rewrite", "send_email_draft")
graph_builder.add_edge("send_email_draft", "human_node")
graph_builder.add_edge("mark_as_read_node", END)
graph_builder.add_edge("notify", "human_node")
graph_builder.add_conditional_edges("human_node", enter_after_human)
graph = graph_builder.compile()