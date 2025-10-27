import AI
import os
from Bot import Instance, Bot
import json

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
TEST = os.getenv("TEST")

instances = [Instance.new(CLIENT_ID, CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD)]

bot = Bot(instances, TEST)

def get_prompt(name):
    return open(f"{name}-prompt.md", "r").read()

def get_subreddits(opinion):
    p = get_prompt("find-subs")
    return AI.infer(p, opinion).split("\n")

def filter_posts(posts, opinion):
    if posts == []:
        return []
    prompt = "\n"
    prompt += f"Opinion: {opinion}\n"
    for i, post in enumerate(posts):
        prompt += f"=== Post {i+1} ===\n"
        prompt += post.title
        prompt += "\n"
        prompt += post.selftext
        prompt += "\n"

    relevant_posts = AI.infer(get_prompt("filter-posts"), prompt).split(",")
    relevant_posts = [int(i) for i in relevant_posts]

    return [posts[i-1] for i in relevant_posts]

def filter_comments(posts, count, opinion):
    if posts == []:
        return []
    all_comments = []
    for post in posts:
        comments = post.comments
        for i in range(count):
            try:
                all_comments.append(comments[i])
            except IndexError:
                break

    if not all_comments:
        return []

    prompt = "\n"
    prompt += f"Opinion: {opinion}\n"
    for i, comment in enumerate(all_comments):
        prompt += f"=== Comment {i+1} ===\n"
        prompt += comment.body
        prompt += "\n"

    relevant_comments = AI.infer(get_prompt("filter-comments"), prompt).split(",")
    relevant_comments = [int(i) for i in relevant_comments]

    return [all_comments[i-1] for i in relevant_comments]

def reply(comments, op):
    prompt = "\n"
    prompt += f"Opinion: {op}\n"
    for i, comment in enumerate(comments):
        prompt += f"=== Comment {i+1} ===\n"
        prompt += comment.body
        prompt += "\n"

    replies = AI.infer(get_prompt("generate-reply"), prompt)
    replies = json.loads(replies)

    for i in range(len(comments)):
        bot.comment(comments[i], replies[i])

def spread_opinion(op, post_count, comment_count):
    subs = get_subreddits(op)
    ps = bot.get_posts(subs, post_count)
    ps = filter_posts(ps, op)
    cs = filter_comments(ps, comment_count, op)
    reply(cs, op)

