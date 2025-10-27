import praw
import random
import os

class Instance:
    def __init__(self, client_id, client_secret, username, password, userid):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            password=password,
            username=username,
            user_agent="FogMachine",
        )

        self.userid = userid

class Bot:
    def __init__(self, instances, test):
        self.instances = instances
        self.test = test

    @property
    def reddit(self):
        i = random.choice(self.instances)
        self.userid = i.userid
        return i.reddit

    def comment(self, c, text):
        """
        This function posts a comment on a Reddit post given its ID and the comment text.
        """
        if self.test:
            print(f"[BOT] Comment: {c['body']}")
            print(f"[BOT] Reply: {text}")
            print()
            return {
                "user_id": self.userid,
                "url": f"https://reddit.com{c['permalink']}",
                "original_comment": c,
                "reply_text": text
            }
        
        reply_obj = c["_praw_obj"].reply(text)
        url = reply_obj.permalink
        
        return {
            "user_id": self.userid,
            "url": f"https://reddit.com{url}",
            "original_comment": c,
            "reply_text": text
        }

    def get_posts(self, subs, count):
        posts = []
        for sub in subs:
            # Use .hot() instead of .stream.submissions() to get a finite list
            for submission in self.reddit.subreddit(sub).hot(limit=count):
                posts.append({
                    "id": submission.id,
                    "title": submission.title,
                    "selftext": submission.selftext,
                    "url": submission.url,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "subreddit": submission.subreddit.display_name,
                    "author": submission.author.name if submission.author else "[deleted]",
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "_praw_obj": submission
                })
        
        if self.test:
            for post in posts:
                print(f"[BOT] Post: {post['title']}")
                print(f"[BOT] Post: {post['selftext']}")
                print(f"[BOT] Post: {post['id']}")
                print()

        return posts

    
