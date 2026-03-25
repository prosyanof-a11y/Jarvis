import BetterSqlite3 from "better-sqlite3";
import { existsSync, mkdirSync } from "fs";

export class Database {
  constructor(path = "./data/autopilot.db") {
    if (!existsSync("./data")) mkdirSync("./data", { recursive: true });
    this.db = new BetterSqlite3(path);
    this.db.pragma("journal_mode = WAL");
  }

  init() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL, topic TEXT, platform TEXT, style TEXT, hashtags TEXT,
        published INTEGER DEFAULT 0, published_to TEXT,
        created_at TEXT DEFAULT (datetime('now')), published_at TEXT
      );
      CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT, title TEXT, description TEXT, link TEXT, source_name TEXT, date TEXT,
        created_at TEXT DEFAULT (datetime('now'))
      );
      CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cron_expression TEXT NOT NULL, description TEXT NOT NULL,
        active INTEGER DEFAULT 1, last_run TEXT, created_at TEXT DEFAULT (datetime('now'))
      );
      CREATE TABLE IF NOT EXISTS stats (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        tokens_used INTEGER DEFAULT 0, ruflo_tasks INTEGER DEFAULT 0
      );
      INSERT OR IGNORE INTO stats (id, tokens_used, ruflo_tasks) VALUES (1, 0, 0);
    `);
  }

  saveDraft(post) {
    return this.db.prepare("INSERT INTO drafts (text,topic,platform,style,hashtags) VALUES (?,?,?,?,?)")
      .run(post.text, post.topic||"", post.platform||"", post.style||"", post.hashtags||"").lastInsertRowid;
  }
  getDraft(id) { return this.db.prepare("SELECT * FROM drafts WHERE id=?").get(id); }
  getRecentDrafts(limit=5) { return this.db.prepare("SELECT * FROM drafts WHERE published=0 ORDER BY created_at DESC LIMIT ?").all(limit); }
  markPublished(id, platform) { this.db.prepare("UPDATE drafts SET published=1, published_to=?, published_at=datetime('now') WHERE id=?").run(platform, id); }
  deleteDraft(id) { this.db.prepare("DELETE FROM drafts WHERE id=?").run(id); }
  clearDrafts() { this.db.prepare("DELETE FROM drafts").run(); }

  saveSource(url, item) { this.db.prepare("INSERT INTO sources (url,title,description,link,source_name,date) VALUES (?,?,?,?,?,?)").run(url, item.title, item.description, item.link, item.source, item.date); }
  getRecentSources(limit=20) { return this.db.prepare("SELECT * FROM sources ORDER BY created_at DESC LIMIT ?").all(limit); }
  clearSources() { this.db.prepare("DELETE FROM sources").run(); }

  saveTask(task) { return this.db.prepare("INSERT INTO tasks (cron_expression,description,active) VALUES (?,?,?)").run(task.cronExpression, task.description, task.active?1:0).lastInsertRowid; }
  getTasks() { return this.db.prepare("SELECT * FROM tasks").all(); }
  updateTaskLastRun(id) { this.db.prepare("UPDATE tasks SET last_run=datetime('now') WHERE id=?").run(id); }

  addTokens(n) { this.db.prepare("UPDATE stats SET tokens_used=tokens_used+? WHERE id=1").run(n); }
  incrementRufloTasks() { this.db.prepare("UPDATE stats SET ruflo_tasks=ruflo_tasks+1 WHERE id=1").run(); }
  getStats() {
    return {
      drafts: this.db.prepare("SELECT COUNT(*) as c FROM drafts").get().c,
      published: this.db.prepare("SELECT COUNT(*) as c FROM drafts WHERE published=1").get().c,
      sources: this.db.prepare("SELECT COUNT(*) as c FROM sources").get().c,
      tasks: this.db.prepare("SELECT COUNT(*) as c FROM tasks WHERE active=1").get().c,
      tokensUsed: (this.db.prepare("SELECT tokens_used FROM stats WHERE id=1").get()?.tokens_used||0).toLocaleString(),
      rufloTasks: this.db.prepare("SELECT ruflo_tasks FROM stats WHERE id=1").get()?.ruflo_tasks||0,
    };
  }
}
