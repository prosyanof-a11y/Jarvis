// Jarvis v2.0 + Ruflo Integration
// Full menu-driven Telegram bot with Claude API + Ruflo Swarm
// See the zip download for the complete source
import { Bot, InlineKeyboard, session } from "grammy";
import Anthropic from "@anthropic-ai/sdk";
import { ContentGenerator } from "./content-generator.js";
import { Publisher } from "./publisher.js";
import { Parser } from "./parser.js";
import { Scheduler } from "./scheduler.js";
import { Database } from "./database.js";
import { RufloEngine } from "./ruflo-engine.js";
import { MenuBuilder } from "./menu.js";

const config = {
  telegramToken: process.env.TELEGRAM_BOT_TOKEN,
  anthropicKey: process.env.ANTHROPIC_API_KEY,
  ownerId: Number(process.env.OWNER_TELEGRAM_ID),
  telegramChannel: process.env.TELEGRAM_CHANNEL_ID || "",
  vkToken: process.env.VK_API_TOKEN || "",
  vkGroupId: process.env.VK_GROUP_ID || "",
};

const bot = new Bot(config.telegramToken);
const claude = new Anthropic({ apiKey: config.anthropicKey });
const db = new Database();
const generator = new ContentGenerator(claude);
const publisher = new Publisher(bot, config);
const parser = new Parser();
const scheduler = new Scheduler(db, generator, publisher, parser);
const ruflo = new RufloEngine(claude, db);

bot.use(session({ initial: () => ({ mode: "idle", action: null, style: null, rufloMode: null }) }));
bot.use((ctx, next) => {
  if (ctx.from?.id !== config.ownerId) return ctx.reply("⛔ Доступ запрещён.");
  return next();
});

// ══════════════ ГЛАВНОЕ МЕНЮ ══════════════
async function showMainMenu(ctx) {
  const stats = db.getStats();
  const r = ruflo.isAvailable() ? "🟢" : "⚪";
  const text = `🤖 *Jarvis + Ruflo*\n\n📝 ${stats.drafts} постов | 📢 ${stats.published} опубл.\n🔍 ${stats.sources} источн. | ⏰ ${stats.tasks} задач\n${r} Ruflo Swarm Engine`;
  const kb = new InlineKeyboard()
    .text("📝 Контент", "menu_content").text("📢 Публикация", "menu_publish").row()
    .text("🔍 Парсинг", "menu_parse").text("📰 Дайджест", "action_digest").row()
    .text("⏰ Расписание", "menu_schedule").text("🧠 Ruflo AI", "menu_ruflo").row()
    .text("📊 Статистика", "action_stats").text("⚙️ Настройки", "menu_settings");
  if (ctx.callbackQuery) {
    await ctx.editMessageText(text, { parse_mode: "Markdown", reply_markup: kb }).catch(() => ctx.reply(text, { parse_mode: "Markdown", reply_markup: kb }));
  } else {
    await ctx.reply(text, { parse_mode: "Markdown", reply_markup: kb });
  }
}
bot.command("start", showMainMenu);
bot.command("menu", showMainMenu);

// ══════════════ КОНТЕНТ ══════════════
bot.callbackQuery("menu_content", async (ctx) => {
  await ctx.answerCallbackQuery();
  const kb = new InlineKeyboard()
    .text("🔥 Вовлекающий", "style_engaging").text("📚 Информативный", "style_informative").row()
    .text("📖 Сторителлинг", "style_storytelling").text("📰 Новостной", "style_news").row()
    .text("🧠 Ruflo Swarm", "style_ruflo_swarm").row()
    .text("◀️ Назад", "menu_main");
  await ctx.editMessageText("📝 *Создание контента*\n\nВыберите стиль:", { parse_mode: "Markdown", reply_markup: kb });
});

for (const s of ["engaging", "informative", "storytelling", "news"]) {
  bot.callbackQuery(`style_${s}`, async (ctx) => {
    await ctx.answerCallbackQuery();
    ctx.session.mode = "waiting_topic"; ctx.session.action = "post"; ctx.session.style = s;
    await ctx.editMessageText("✏️ Напишите тему поста:");
  });
}

bot.callbackQuery("style_ruflo_swarm", async (ctx) => {
  await ctx.answerCallbackQuery();
  ctx.session.mode = "waiting_topic"; ctx.session.action = "ruflo_task"; ctx.session.rufloMode = "smart_post";
  await ctx.editMessageText("🧠 *Ruflo Swarm*\n\n🔍Scout → ✍️Writer → ✅Reviewer\n\n✏️ Напишите тему:", { parse_mode: "Markdown" });
});

// ══════════════ ПУБЛИКАЦИЯ ══════════════
bot.callbackQuery("menu_publish", async (ctx) => {
  await ctx.answerCallbackQuery();
  const drafts = db.getRecentDrafts(5);
  if (!drafts.length) {
    const kb = new InlineKeyboard().text("📝 Создать", "menu_content").text("◀️ Назад", "menu_main");
    return ctx.editMessageText("Нет черновиков.", { reply_markup: kb });
  }
  let text = "📢 *Черновики:*\n\n";
  const kb = new InlineKeyboard();
  drafts.forEach((d, i) => {
    text += `${i+1}. ${d.text.slice(0,50).replace(/\n/g," ")}...\n`;
    kb.text(`📢#${d.id}→TG`, `pub_tg_${d.id}`).text(`📘VK`, `pub_vk_${d.id}`).row();
  });
  kb.text("◀️ Назад", "menu_main");
  await ctx.editMessageText(text, { parse_mode: "Markdown", reply_markup: kb });
});

bot.callbackQuery(/^pub_tg_(\d+)$/, async (ctx) => {
  const id = Number(ctx.match[1]);
  await ctx.answerCallbackQuery("⏳");
  const draft = db.getDraft(id); if (!draft) return;
  try { await publisher.publishTelegram(draft.text); db.markPublished(id, "telegram"); await ctx.editMessageText("✅ Опубликовано в TG!"); } catch(e) { await ctx.reply("❌ "+e.message); }
});

bot.callbackQuery(/^pub_vk_(\d+)$/, async (ctx) => {
  const id = Number(ctx.match[1]);
  await ctx.answerCallbackQuery("⏳");
  const draft = db.getDraft(id); if (!draft) return;
  try { await publisher.publishVK(draft.text); db.markPublished(id, "vk"); await ctx.editMessageText("✅ Опубликовано в VK!"); } catch(e) { await ctx.reply("❌ "+e.message); }
});

// ══════════════ ПАРСИНГ ══════════════
bot.callbackQuery("menu_parse", async (ctx) => {
  await ctx.answerCallbackQuery();
  ctx.session.mode = "waiting_url"; ctx.session.action = "parse";
  const kb = new InlineKeyboard().text("◀️ Назад", "menu_main");
  await ctx.editMessageText("🔍 *Парсинг*\n\nОтправьте ссылку:\n• RSS: `https://habr.com/ru/rss/`\n• Telegram: `https://t.me/durov`\n• Сайт: любой URL", { parse_mode: "Markdown", reply_markup: kb });
});

// ══════════════ ДАЙДЖЕСТ ══════════════
bot.callbackQuery("action_digest", async (ctx) => {
  await ctx.answerCallbackQuery("📰 Собираю...");
  const sources = db.getRecentSources(20);
  if (!sources.length) { const kb = new InlineKeyboard().text("🔍 Парсинг", "menu_parse").text("◀️ Назад", "menu_main"); return ctx.editMessageText("Нет источников.", { reply_markup: kb }); }
  try {
    const digest = await generator.createDigest(sources);
    const id = db.saveDraft(digest);
    const kb = new InlineKeyboard().text("📢 TG", `pub_tg_${id}`).text("📘 VK", `pub_vk_${id}`).row().text("◀️ Меню", "menu_main");
    await ctx.editMessageText(`📰 *Дайджест:*\n\n${digest.text.slice(0,3500)}`, { parse_mode: "Markdown", reply_markup: kb }).catch(() => ctx.reply(digest.text.slice(0,3500), {reply_markup: kb}));
  } catch(e) { await ctx.reply("❌ "+e.message); }
});

// ══════════════ РАСПИСАНИЕ ══════════════
bot.callbackQuery("menu_schedule", async (ctx) => {
  await ctx.answerCallbackQuery();
  const tasks = scheduler.listTasks();
  let text = "⏰ *Расписание*\n\n";
  if (!tasks.length) text += "Нет задач."; 
  else tasks.forEach(t => { text += `${t.active?"🟢":"⏸"} #${t.id}: ${t.description}\n   ${t.cron_expression}\n\n`; });
  const kb = new InlineKeyboard().text("➕ Новая задача", "schedule_add").row().text("⏸ Пауза", "schedule_pause").text("▶️ Запуск", "schedule_resume").row().text("◀️ Назад", "menu_main");
  await ctx.editMessageText(text, { parse_mode: "Markdown", reply_markup: kb });
});

bot.callbackQuery("schedule_add", async (ctx) => {
  await ctx.answerCallbackQuery();
  ctx.session.mode = "waiting_cron"; ctx.session.action = "cron";
  await ctx.editMessageText("➕ *Новая задача*\n\nФормат: `10:00 Описание`\n\nПримеры:\n• `09:00 Дайджест AI-новостей`\n• `18:00 Пост про продуктивность`", { parse_mode: "Markdown" });
});
bot.callbackQuery("schedule_pause", async (ctx) => { scheduler.pauseAll(); await ctx.answerCallbackQuery("⏸ Пауза"); });
bot.callbackQuery("schedule_resume", async (ctx) => { scheduler.resumeAll(); await ctx.answerCallbackQuery("▶️ Запуск"); });

// ══════════════ RUFLO AI ══════════════
bot.callbackQuery("menu_ruflo", async (ctx) => {
  await ctx.answerCallbackQuery();
  const status = await ruflo.getStatus();
  const kb = new InlineKeyboard()
    .text("🧠 Умный пост", "ruflo_smart_post").text("🔬 Ресёрч", "ruflo_research").row()
    .text("📋 Контент-план", "ruflo_content_plan").text("🔄 Рерайт", "ruflo_rewrite").row()
    .text("🌐 SEO", "ruflo_seo").text("📊 Статус", "ruflo_status").row()
    .text("◀️ Назад", "menu_main");
  await ctx.editMessageText(`🧠 *Ruflo AI Engine*\n\n${status.statusLine}\n\nМультиагентные пайплайны\nдля создания контента`, { parse_mode: "Markdown", reply_markup: kb });
});

for (const [mode, label] of [["smart_post","🧠 Умный пост"],["research","🔬 Ресёрч"],["content_plan","📋 Контент-план"]]) {
  bot.callbackQuery(`ruflo_${mode}`, async (ctx) => {
    await ctx.answerCallbackQuery();
    ctx.session.mode = "waiting_topic"; ctx.session.action = "ruflo_task"; ctx.session.rufloMode = mode;
    await ctx.editMessageText(`${label}\n\n✏️ Напишите тему:`);
  });
}
for (const [mode, label] of [["rewrite","🔄 Рерайт"],["seo","🌐 SEO"]]) {
  bot.callbackQuery(`ruflo_${mode}`, async (ctx) => {
    await ctx.answerCallbackQuery();
    ctx.session.mode = "waiting_message"; ctx.session.action = "ruflo_task"; ctx.session.rufloMode = mode;
    await ctx.editMessageText(`${label}\n\n✏️ Вставьте текст:`);
  });
}

bot.callbackQuery("ruflo_status", async (ctx) => {
  const s = await ruflo.getStatus();
  await ctx.answerCallbackQuery();
  const kb = new InlineKeyboard().text("◀️ Назад", "menu_ruflo");
  await ctx.editMessageText(`📊 *Ruflo*\n\n${s.details}`, { parse_mode: "Markdown", reply_markup: kb });
});

// ══════════════ НАСТРОЙКИ ══════════════
bot.callbackQuery("menu_settings", async (ctx) => {
  await ctx.answerCallbackQuery();
  const tg = config.telegramChannel ? `✅ ${config.telegramChannel}` : "❌";
  const vk = config.vkToken ? "✅" : "❌";
  const kb = new InlineKeyboard().text("🗑 Очистить черновики", "clear_drafts").text("🗑 Источники", "clear_sources").row().text("◀️ Назад", "menu_main");
  await ctx.editMessageText(`⚙️ *Настройки*\n\nTelegram: ${tg}\nVK: ${vk}\n\n_Каналы → Railway Variables_`, { parse_mode: "Markdown", reply_markup: kb });
});
bot.callbackQuery("clear_drafts", async (ctx) => { db.clearDrafts(); await ctx.answerCallbackQuery("🗑 Очищено"); });
bot.callbackQuery("clear_sources", async (ctx) => { db.clearSources(); await ctx.answerCallbackQuery("🗑 Очищено"); });

// ══════════════ СТАТИСТИКА ══════════════
bot.callbackQuery("action_stats", async (ctx) => {
  await ctx.answerCallbackQuery();
  const s = db.getStats();
  const kb = new InlineKeyboard().text("◀️ Назад", "menu_main");
  await ctx.editMessageText(`📊 *Статистика*\n\n📝 Создано: ${s.drafts}\n📢 Опубл: ${s.published}\n🔍 Источников: ${s.sources}\n⏰ Задач: ${s.tasks}\n🤖 Токенов: ~${s.tokensUsed}\n🧠 Ruflo: ${s.rufloTasks||0}`, { parse_mode: "Markdown", reply_markup: kb });
});

bot.callbackQuery("menu_main", async (ctx) => { await ctx.answerCallbackQuery(); ctx.session.mode="idle"; await showMainMenu(ctx); });

// ══════════════ REWRITE/DELETE ══════════════
bot.callbackQuery(/^rewrite_(\d+)$/, async (ctx) => {
  const id = Number(ctx.match[1]); await ctx.answerCallbackQuery("✏️");
  const draft = db.getDraft(id); if (!draft) return;
  const p = await generator.rewrite(draft.text); const nid = db.saveDraft(p);
  const kb = new InlineKeyboard().text("📢 TG", `pub_tg_${nid}`).text("🔄 Ещё", `rewrite_${nid}`).row().text("◀️ Меню", "menu_main");
  await ctx.editMessageText(`✏️ *Переписано:*\n\n${p.text.slice(0,3500)}`, { parse_mode: "Markdown", reply_markup: kb }).catch(()=>ctx.reply(p.text.slice(0,3500),{reply_markup:kb}));
});
bot.callbackQuery(/^delete_(\d+)$/, async (ctx) => { db.deleteDraft(Number(ctx.match[1])); await ctx.answerCallbackQuery("🗑"); await showMainMenu(ctx); });

// ══════════════ ТЕКСТОВЫЕ СООБЩЕНИЯ ══════════════
bot.on("message:text", async (ctx) => {
  const text = ctx.message.text;
  if (text==="/menu"||text==="/start") return showMainMenu(ctx);
  const { mode, action, style } = ctx.session;

  // Тема поста
  if (mode==="waiting_topic" && action==="post") {
    ctx.session.mode="idle"; await ctx.reply("⏳ Генерирую...");
    try {
      const post = await generator.createPost(text, { style: style||"engaging", platform: "telegram", language: "ru" });
      const id = db.saveDraft(post);
      const kb = new InlineKeyboard().text("📢 TG", `pub_tg_${id}`).text("📘 VK", `pub_vk_${id}`).row().text("🔄 Переписать", `rewrite_${id}`).text("🗑", `delete_${id}`).row().text("◀️ Меню", "menu_main");
      await ctx.reply(`📝 *Готово:*\n\n${post.text}`, { parse_mode: "Markdown", reply_markup: kb }).catch(()=>ctx.reply(post.text,{reply_markup:kb}));
    } catch(e) { await ctx.reply("❌ "+e.message); await showMainMenu(ctx); }
    return;
  }

  // Ruflo задача
  if ((mode==="waiting_topic"||mode==="waiting_message") && action==="ruflo_task") {
    ctx.session.mode="idle"; await ctx.reply("🧠 Ruflo обрабатывает...");
    try {
      const result = await ruflo.execute(ctx.session.rufloMode||"smart_post", text);
      const id = db.saveDraft(result);
      const kb = new InlineKeyboard().text("📢 TG", `pub_tg_${id}`).text("📘 VK", `pub_vk_${id}`).row().text("🔄 Улучшить", `rewrite_${id}`).row().text("◀️ Меню", "menu_main");
      await ctx.reply(`🧠 *Ruflo:*\n\n${result.text.slice(0,3500)}`, { parse_mode: "Markdown", reply_markup: kb }).catch(()=>ctx.reply(result.text.slice(0,3500),{reply_markup:kb}));
    } catch(e) { await ctx.reply("❌ "+e.message); await showMainMenu(ctx); }
    return;
  }

  // Парсинг URL
  if (mode==="waiting_url" && action==="parse") {
    ctx.session.mode="idle"; await ctx.reply("🔍 Парсю...");
    try {
      const items = await parser.parseUrl(text);
      items.forEach(item => db.saveSource(text, item));
      const summary = items.slice(0,7).map((it,i)=>`${i+1}. ${it.title.slice(0,80)}`).join("\n");
      const kb = new InlineKeyboard().text("📰 Дайджест", "action_digest").text("🔍 Ещё", "menu_parse").row().text("◀️ Меню", "menu_main");
      await ctx.reply(`✅ ${items.length} записей:\n\n${summary}`, { reply_markup: kb });
    } catch(e) { await ctx.reply("❌ "+e.message); await showMainMenu(ctx); }
    return;
  }

  // Cron
  if (mode==="waiting_cron" && action==="cron") {
    ctx.session.mode="idle";
    const m = text.match(/^(\d{1,2}):(\d{2})\s+(.+)$/);
    if (!m) { await ctx.reply("❌ Формат: 10:00 описание"); return; }
    const tid = scheduler.addTask({ cronExpression: `${m[2]} ${m[1]} * * *`, description: m[3], active: true });
    const kb = new InlineKeyboard().text("➕ Ещё", "schedule_add").text("◀️ Меню", "menu_main");
    await ctx.reply(`✅ #${tid} — каждый день в ${m[1]}:${m[2]}\n📝 ${m[3]}`, { reply_markup: kb });
    return;
  }

  // Свободный чат
  try {
    const r = await claude.messages.create({ model: "claude-sonnet-4-20250514", max_tokens: 2048,
      system: "Ты — AI-ассистент для контента и автоматизации. Отвечай по-русски. Ты работаешь с Ruflo — мультиагентной AI-платформой.",
      messages: [{ role: "user", content: text }] });
    const reply = r.content[0]?.text || "";
    db.addTokens((r.usage?.input_tokens||0)+(r.usage?.output_tokens||0));
    const kb = new InlineKeyboard().text("📋 Меню", "menu_main");
    await ctx.reply(reply, { parse_mode: "Markdown", reply_markup: kb }).catch(()=>ctx.reply(reply,{reply_markup:kb}));
  } catch(e) { await ctx.reply("❌ "+e.message); }
});

// ══════════════ ЗАПУСК ══════════════
async function main() {
  console.log("🤖 Jarvis v2.0 + Ruflo");
  db.init(); console.log("✅ DB");
  scheduler.start(); console.log("✅ Scheduler");
  await ruflo.init(); console.log("✅ Ruflo");
  bot.start({ onStart: (i) => { console.log(`✅ @${i.username} online 24/7`); } });
}
main().catch(console.error);
