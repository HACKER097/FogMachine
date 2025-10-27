Your goal is to return top 3 relevant subreddits (if possible) which are most likely to contain discussions about the given topic.

Follow this format:
1. Return a json array of relevant subreddits. Eg: ["subreddit1", "subreddit2", "subreddit3"]
2. Do not include the 'r/' prefix, just the name of the subreddit. For example, if the subreddit is 'r/AskReddit', the output should be 'AskReddit'
3. Do not return subreddits which are not related to the exact topic, you can return less than 3 subreddits if you cannot find 3 relevant subreddits
4. DO NOT INCLUDE FLUFF OR EXTRA TEXT, ONLY GIVE NAMES
5. Search and make sure that the listed subreddits are real

Here is the topic:
