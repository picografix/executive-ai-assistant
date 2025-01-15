"""Fetches few shot examples for triage step."""

from langgraph.store.base import BaseStore
from eaia.main.twitter.schema import TweetData


template = """Tweet From: {from_handle}
Tweet To: {to_handle}
Tweet Content: 
```
{content}
```
> Triage Result: {result}"""


def format_similar_examples_store(examples):
    strs = ["Here are some previous examples:"]
    for eg in examples:
        strs.append(
            template.format(
                to_email=eg.value["input"]["to_handle"],
                from_email=eg.value["input"]["from_handle"],
                content=eg.value["input"]["tweet_content"][:400],
                result=eg.value["triage"],
            )
        )
    return "\n\n------------\n\n".join(strs)


async def get_few_shot_examples(tweet: TweetData, store: BaseStore, config):
    namespace = (
        config["configurable"].get("assistant_id", "default"),
        "triage_examples",
    )
    result = await store.asearch(namespace, query=str({"input": tweet}), limit=5)
    if result is None:
        return ""
    return format_similar_examples_store(result)
