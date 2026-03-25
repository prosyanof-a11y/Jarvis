// ═══════════════════════════════════════════════════════════
// Ruflo Engine — мультиагентная AI-обработка через Claude
// Имитирует подход Ruflo Swarm: несколько "агентов" с ролями
// работают последовательно над одной задачей
// ═══════════════════════════════════════════════════════════

export class RufloEngine {
  constructor(claude, db) {
    this.claude = claude;
    this.db = db;
    this.available = false;

    // Определяем агентов-ролей
    this.agents = {
      scout: {
        name: "🔍 Scout",
        system:
          "Ты — агент-разведчик. Твоя задача: проанализировать тему, " +
          "выделить ключевые аспекты, найти интересные углы подачи, " +
          "определить целевую аудиторию и актуальность. " +
          "Отвечай структурированно и кратко.",
      },
      writer: {
        name: "✍️ Writer",
        system:
          "Ты — профессиональный копирайтер. На основе предоставленного " +
          "анализа напиши готовый пост. Язык: русский. " +
          "Используй эмодзи, разбивай на абзацы. " +
          "Пост должен быть цепляющим и легко читаемым. " +
          "Добавь 3-5 хештегов в конце. Не используй заголовки с ##.",
      },
      reviewer: {
        name: "✅ Reviewer",
        system:
          "Ты — редактор и контент-ревьюер. Проверь текст на: " +
          "грамматику, логичность, вовлекающий стиль, длину. " +
          "Если текст хороший — верни его без изменений. " +
          "Если нужны правки — внеси их и верни улучшенную версию. " +
          "Верни ТОЛЬКО финальный текст, без комментариев.",
      },
      researcher: {
        name: "🔬 Researcher",
        system:
          "Ты — исследователь-аналитик. Проведи глубокий анализ темы: " +
          "история, текущее состояние, тренды, прогнозы, ключевые игроки, " +
          "статистика и факты. Структурируй информацию. Язык: русский.",
      },
      planner: {
        name: "📋 Planner",
        system:
          "Ты — контент-стратег. Создай детальный контент-план на 7 дней. " +
          "Для каждого дня: тема поста, формат (текст/видео/карусель), " +
          "время публикации, хештеги, призыв к действию. Язык: русский. " +
          "Формат: таблица или нумерованный список по дням.",
      },
      seo: {
        name: "🌐 SEO Expert",
        system:
          "Ты — SEO-специалист. Оптимизируй текст для поисковых систем и " +
          "социальных сетей: добавь ключевые слова, улучши структуру, " +
          "оптимизируй заголовок и описание. " +
          "Верни ТОЛЬКО оптимизированный текст.",
      },
    };
  }

  async init() {
    this.available = true;
    console.log("🧠 Ruflo Engine initialized (multi-agent mode)");
  }

  isAvailable() {
    return this.available;
  }

  async getStatus() {
    const agentList = Object.entries(this.agents)
      .map(([key, a]) => `${a.name} (${key})`)
      .join("\n");

    return {
      statusLine: this.available ? "🟢 Online — Multi-Agent Mode" : "⚪ Offline",
      details:
        `Режим: Multi-Agent Pipeline\n` +
        `Модель: Claude Sonnet 4\n\n` +
        `Доступные агенты:\n${agentList}\n\n` +
        `Pipelines:\n` +
        `• smart_post: Scout → Writer → Reviewer\n` +
        `• research: Researcher → Writer → Reviewer\n` +
        `• content_plan: Planner\n` +
        `• rewrite: Reviewer → Writer\n` +
        `• seo: SEO Expert → Reviewer`,
    };
  }

  // ─── Основной метод выполнения ─────────────────────────
  async execute(mode, input) {
    const pipelines = {
      smart_post: ["scout", "writer", "reviewer"],
      research: ["researcher", "writer", "reviewer"],
      content_plan: ["planner"],
      rewrite: ["reviewer", "writer"],
      seo: ["seo", "reviewer"],
    };

    const pipeline = pipelines[mode] || pipelines.smart_post;
    let context = input;
    let allTokens = 0;

    console.log(`🧠 Ruflo: executing pipeline [${pipeline.join(" → ")}]`);

    for (const agentKey of pipeline) {
      const agent = this.agents[agentKey];
      console.log(`  ${agent.name} processing...`);

      const response = await this.claude.messages.create({
        model: "claude-sonnet-4-20250514",
        max_tokens: 3000,
        system: agent.system,
        messages: [
          {
            role: "user",
            content:
              pipeline.indexOf(agentKey) === 0
                ? context
                : `Вот результат предыдущего этапа:\n\n${context}\n\nОбработай и улучши.`,
          },
        ],
      });

      context = response.content[0]?.text || context;
      allTokens += (response.usage?.input_tokens || 0) + (response.usage?.output_tokens || 0);
    }

    this.db.addTokens(allTokens);
    this.db.incrementRufloTasks();

    return {
      text: context,
      topic: input.slice(0, 100),
      platform: "telegram",
      style: mode,
      createdAt: new Date().toISOString(),
      tokens: allTokens,
      pipeline: pipeline.join(" → "),
    };
  }
}
