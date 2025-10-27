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
            prompt += post['title']
            prompt += "\n"
            prompt += post['selftext']
            prompt += "\n"

        relevant_posts_indices = AI.infer(self.get_prompt("filter-posts"), prompt)
        relevant_posts_indices = json.loads(relevant_posts_indices)
        relevant_posts_indices = [int(i) for i in relevant_posts_indices]

        return [posts[i-1] for i in relevant_posts_indices]

    def filter_comments(self, posts, count, opinion):
        if posts == []:
            return []
        all_comments = []
        for post in posts:
            comments = post["_praw_obj"].comments
            for i in range(count):
                try:
                    comment = comments[i]
                    all_comments.append({
                        "id": comment.id,
                        "body": comment.body,
                        "permalink": f"https://reddit.com{comment.permalink}",
                        "author": comment.author.name if comment.author else "[deleted]",
                        "score": comment.score,
                        "created_utc": comment.created_utc,
                        "_praw_obj": comment
                    })
                except IndexError:
                    break

        if not all_comments:
            return []

        prompt = "\n"
        prompt += f"Opinion: {opinion}\n"
        for i, comment in enumerate(all_comments):
            prompt += f"=== Comment {i+1} ===\n"
            prompt += comment['body']
            prompt += "\n"

        relevant_comments_indices = AI.infer(self.get_prompt("filter-comments"), prompt)
        relevant_comments_indices = json.loads(relevant_comments_indices)
        relevant_comments_indices = [int(i) for i in relevant_comments_indices]

        return [all_comments[i-1] for i in relevant_comments_indices]

    def reply(self, comments, op):
        prompt = "\n"
        prompt += f"Opinion: {op}\n"
        for i, comment in enumerate(comments):
            prompt += f"=== Comment {i+1} ===\n"
            prompt += comment['body']
            prompt += "\n"

        replies_text = AI.infer(self.get_prompt("generate-reply"), prompt)
        replies_text = json.loads(replies_text)

        rs = []
  
        for i in range(len(comments)):
            r = self.bot.comment(comments[i], replies_text[i])
            rs.append(r)

        return rs

    def spread_opinion(self, op, post_count, comment_count, subreddits):
        yield {"status": "Getting posts"}
        ps = self.bot.get_posts(subreddits, post_count)
        # Remove non-serializable object before yielding
        yield {"status": "Got posts", "posts": [{k: v for k, v in p.items() if k != '_praw_obj'} for p in ps]}

        yield {"status": "Filtering posts"}
        ps = self.filter_posts(ps, op)
        yield {"status": "Filtered posts", "posts": [{k: v for k, v in p.items() if k != '_praw_obj'} for p in ps]}

        yield {"status": "Filtering comments"}
        cs = self.filter_comments(ps, comment_count, op)
        yield {"status": "Filtered comments", "comments": [{k: v for k, v in c.items() if k != '_praw_obj'} for c in cs]}

        if cs == []:
            return

        yield {"status": "Replying to comments"}
        replies = self.reply(cs, op)
        # The _praw_obj in original_comment needs to be removed
        for r in replies:
            if 'original_comment' in r and '_praw_obj' in r['original_comment']:
                del r['original_comment']['_praw_obj']

        yield {"status": "Finished replying", "replies": replies}



# m = FogMachine(instances, TEST)
# m.spread_opinion("Pizza is the best", 5, 5)
