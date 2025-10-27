DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS credentials;
DROP TABLE IF EXISTS campaigns;
DROP TABLE IF EXISTS logs;

CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('worker', 'provider'))
);

CREATE TABLE credentials (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  client_id TEXT NOT NULL,
  client_secret TEXT NOT NULL,
  reddit_username TEXT NOT NULL,
  reddit_password TEXT NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users (id)
);

CREATE TABLE campaigns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider_id INTEGER NOT NULL,
  opinion TEXT NOT NULL,
  post_count INTEGER NOT NULL,
  comment_count INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  FOREIGN KEY (provider_id) REFERENCES users (id)
);

CREATE TABLE logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER NOT NULL,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  message TEXT NOT NULL,
  FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
);
