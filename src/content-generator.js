export class ContentGenerator {
  constructor(claude) { this.claude = claude; }

  async createPost(topic, options = {}) {
    const { style = "engaging", platform = "telegram", language = "ru" } = options;
    const platformGuide = { telegram: "Для Telegram: короткий, ёмкий, с эмодзи и хештегами. Макс 2000 символов.", vk: "Для VK: развёрнутый, с призывом к действию.", universal: "Универсальный пост." };
    const styleGuide = { engaging: "Вовлекающий: цепляющий заголовок, интрига, вопросы.", informative: "Информативный: факты, цифры, выводы.", storytelling: "Сторителлинг: история, эмоции.", news: "Новостной: кратко, объективно." };
    const r = await this.claude.messages.create({ model: "claude-sonnet-4-20250514", max_tokens: 2048,
      system: `Ты — профессиональный копирайтер. Язык: ${language==="ru"?"русский":"English"}. ${platformGuide[platform]||platformGuide.universal} ${styleGuide[style]||styleGuide.engaging} В конце 3-5 хештегов. НЕ используй ## заголовки. Используй эмодзи.`,
      messages: [{ role: "user", content: `Напиши пост на тему: "${topic}"` }] });
    const text = r.content[0]?.text || "";
    return { text, hashtags: text.match(/#\S+/g)?.join(" ")||"", topic, platform, style, createdAt: new Date().toISOString(), tokens: (r.usage?.input_tokens||0)+(r.usage?.output_tokens||0) };
  }

  async createDigest(sources, options = {}) {
    const { language = "ru", maxItems = 10 } = options;
    const src = sources.slice(0,maxItems).map((s,i)=>`${i+1}. ${s.title}: ${s.description||s.link||""}`).join("\n");
    const r = await this.claude.messages.create({ model: "claude-sonnet-4-20250514", max_tokens: 3000,
      system: "Ты — редактор дайджеста. Русский. Создай краткий дайджест. Эмодзи. Хештеги в конце.",
      messages: [{ role: "user", content: `Источники:\n\n${src}` }] });
    return { text: r.content[0]?.text||"", topic: "digest", platform: "telegram", style: "news", createdAt: new Date().toISOString() };
  }

  async rewrite(originalText) {
    const r = await this.claude.messages.create({ model: "claude-sonnet-4-20250514", max_tokens: 2048,
      system: "Перепиши текст, сохранив смысл. Сделай цепляющим. Верни ТОЛЬКО текст.",
      messages: [{ role: "user", content: `Перепиши:\n\n${originalText}` }] });
    return { text: r.content[0]?.text||"", topic: "rewrite", createdAt: new Date().toISOString() };
  }
}
