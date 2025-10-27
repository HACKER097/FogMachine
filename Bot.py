import praw
import random
import os

class Instance:
    def __init__(self):
        pass

    def new(client_id, client_secret, username, password):
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            password=password,
            username=username,
            user_agent="FogMachine",
        )

        return reddit

class Bot:
    def __init__(self, instances, test):
        self.instances = instances
        self.test = test

    @property
    def reddit(self):
        return random.choice(self.instances)

    def comment(self, c, text):
        """
        This function posts a comment on a Reddit post given its ID and the comment text.
        """
        if self.test:
            print(f"[BOT] Comment: {c.body}")
            print(f"[BOT] Reply: {text}")
            print()
            return
        c.reply(text)

    def get_posts(self, subs, count):
        posts = []
        for sub in subs:
            c = count
            submissions = self.reddit.subreddit(sub).stream.submissions()
            for submission in submissions:
                posts.append(submission)
                c -= 1
                if not c:
                    break
           
        if self.test:
            for post in posts:
                print(f"[BOT] Post: {post.title}")
                print(f"[BOT] Post: {post.selftext}")
                print(f"[BOT] Post: {post.id}")
                print()

        return posts

    
