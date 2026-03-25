import axios from "axios";

export class Publisher {
  constructor(bot, config) { this.bot = bot; this.config = config; }

  async publishTelegram(text, options = {}) {
    const cid = options.channelId || this.config.telegramChannel;
    if (!cid) throw new Error("TELEGRAM_CHANNEL_ID не настроен");
    await this.bot.api.sendMessage(cid, text, { parse_mode: "Markdown" }).catch(() => this.bot.api.sendMessage(cid, text));
    return { platform: "telegram", channelId: cid, timestamp: new Date().toISOString() };
  }

  async publishVK(text) {
    const { vkToken: token, vkGroupId: gid } = this.config;
    if (!token || !gid) throw new Error("VK не настроен (VK_API_TOKEN, VK_GROUP_ID)");
    const r = await axios.get("https://api.vk.com/method/wall.post", { params: { owner_id: `-${gid}`, from_group: 1, message: text, access_token: token, v: "5.199" } });
    if (r.data.error) throw new Error(`VK: ${r.data.error.error_msg}`);
    return { platform: "vk", postId: r.data.response?.post_id, timestamp: new Date().toISOString() };
  }

  async publishAll(text) {
    const results = [];
    if (this.config.telegramChannel) try { results.push(await this.publishTelegram(text)); } catch(e) { results.push({ platform:"telegram", error:e.message }); }
    if (this.config.vkToken) try { results.push(await this.publishVK(text)); } catch(e) { results.push({ platform:"vk", error:e.message }); }
    return results;
  }
}
