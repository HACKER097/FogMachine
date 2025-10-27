import AI
import os
from Bot import Instance, Bot
import json

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDDIT_USERNAME = os.getenv("REDDIT_USERNAME")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
TEST = os.getenv("TEST")

instances = [Instance(CLIENT_ID, CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD, "hello")]

class FogMachine:
    def __init__(self, instances, test):
        self.instances = instances
        self.test = test
        self.bot = Bot(instances, test)

    def get_prompt(self, name):
        return open(f"{name}-prompt.md", "r").read()

    def get_subreddits(self, opinion):
        p = self.get_prompt("find-subs")
        return json.loads(AI.infer(p, opinion))

    def filter_posts(self, posts, opinion):
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

        relevant_posts = AI.infer(self.get_prompt("filter-posts"), prompt)
        relevant_posts = json.loads(relevant_posts)
        relevant_posts = [int(i) for i in relevant_posts]

        return [posts[i-1] for i in relevant_posts]

    def filter_comments(self, posts, count, opinion):
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

        relevant_comments = AI.infer(self.get_prompt("filter-comments"), prompt)
        relevant_comments = json.loads(relevant_comments)
        relevant_comments = [int(i) for i in relevant_comments]

        return [all_comments[i-1] for i in relevant_comments]

    def reply(self, comments, op):
        prompt = "\n"
        prompt += f"Opinion: {op}\n"
        for i, comment in enumerate(comments):
            prompt += f"=== Comment {i+1} ===\n"
            prompt += comment.body
            prompt += "\n"

        replies = AI.infer(self.get_prompt("generate-reply"), prompt)
        replies = json.loads(replies)

        rs = []
  
        for i in range(len(comments)):
            r = self.bot.comment(comments[i], replies[i])
            rs.append(r)

        return rs

    def spread_opinion(self, op, post_count, comment_count):
        yield {"status": "Finding subreddits"}
        subs = self.get_subreddits(op)
        yield {"status": "Found subreddits", "subreddits": subs}

        yield {"status": "Getting posts"}
        ps = self.bot.get_posts(subs, post_count)
        yield {"status": "Got posts", "count": len(ps)}

        yield {"status": "Filtering posts"}
        ps = self.filter_posts(ps, op)
        yield {"status": "Filtered posts", "count": len(ps)}

        yield {"status": "Filtering comments"}
        cs = self.filter_comments(ps, comment_count, op)
        yield {"status": "Filtered comments", "count": len(cs)}

        if cs == []:
            return

        yield {"status": "Replying to comments"}
        replies = self.reply(cs, op)
        yield {"status": "Finished replying", "replies": replies}



# m = FogMachine(instances, TEST)
# m.spread_opinion("Pizza is the best", 5, 5)
