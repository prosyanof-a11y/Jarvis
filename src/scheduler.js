import cron from "node-cron";

export class Scheduler {
  constructor(db, generator, publisher, parser) { this.db=db; this.generator=generator; this.publisher=publisher; this.parser=parser; this.jobs=new Map(); }

  start() {
    const tasks = this.db.getTasks();
    tasks.filter(t=>t.active).forEach(t => this.scheduleTask(t));
    console.log(`📅 ${tasks.filter(t=>t.active).length} active tasks`);
  }

  addTask(task) { const id = this.db.saveTask(task); this.scheduleTask({...task, id, cron_expression: task.cronExpression}); return id; }

  scheduleTask(task) {
    const expr = task.cron_expression || task.cronExpression;
    if (!cron.validate(expr)) return;
    const job = cron.schedule(expr, async () => {
      console.log(`⏰ Task #${task.id}: ${task.description}`);
      try { await this.executeTask(task); this.db.updateTaskLastRun(task.id); } catch(e) { console.error(`❌ #${task.id}:`, e.message); }
    });
    this.jobs.set(task.id, job);
  }

  async executeTask(task) {
    const d = task.description.toLowerCase();
    if (d.includes("парс")||d.includes("дайджест")||d.includes("новост")) {
      const sources = this.db.getRecentSources(15);
      if (sources.length) { const digest = await this.generator.createDigest(sources); await this.publisher.publishAll(digest.text); this.db.saveDraft({...digest, published:true}); }
    } else {
      const post = await this.generator.createPost(task.description, { style:"engaging", platform:"telegram" });
      await this.publisher.publishAll(post.text); this.db.saveDraft({...post, published:true});
    }
  }

  listTasks() { return this.db.getTasks().map(t => ({...t, active: Boolean(t.active), scheduled: this.jobs.has(t.id)})); }
  pauseAll() { for (const [,j] of this.jobs) j.stop(); }
  resumeAll() { for (const [,j] of this.jobs) j.start(); }
}
