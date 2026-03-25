import axios from "axios";
import * as cheerio from "cheerio";
import RSSParser from "rss-parser";

export class Parser {
  constructor() { this.rssParser = new RSSParser(); this.headers = { "User-Agent": "Mozilla/5.0 Chrome/120.0.0.0" }; }

  async parseUrl(url) {
    if (url.includes("t.me/")) return this.parseTelegram(url);
    try { return await this.parseRSS(url); } catch { return this.parseHTML(url); }
  }

  async parseRSS(url) {
    const feed = await this.rssParser.parseURL(url);
    return feed.items.map(i => ({ title: i.title||"", description: i.contentSnippet||"", link: i.link||"", date: i.isoDate||"", source: feed.title||url }));
  }

  async parseHTML(url) {
    const { data } = await axios.get(url, { headers: this.headers, timeout: 15000 });
    const $ = cheerio.load(data);
    const items = []; const seen = new Set();
    for (const sel of ["article","h2 a","h3 a",".post",".card","[class*='post']"]) {
      $(sel).each((_, el) => {
        const $el = $(el);
        const title = ($el.find("h1,h2,h3,.title").first().text().trim() || $el.text().trim()).slice(0,300);
        const link = $el.find("a").first().attr("href") || $el.attr("href") || "";
        const desc = $el.find("p,.description").first().text().trim().slice(0,500);
        const key = title.slice(0,50);
        if (title.length > 10 && !seen.has(key)) { seen.add(key); items.push({ title, description: desc, link: link.startsWith("http") ? link : new URL(link, url).href, date: new Date().toISOString(), source: url }); }
      });
      if (items.length > 3) break;
    }
    return items;
  }

  async parseTelegram(url) {
    const m = url.match(/t\.me\/([^/?]+)/); if (!m) throw new Error("Не найден канал");
    const { data } = await axios.get(`https://t.me/s/${m[1]}`, { headers: this.headers, timeout: 15000 });
    const $ = cheerio.load(data); const items = [];
    $(".tgme_widget_message_wrap").each((_, el) => {
      const text = $(el).find(".tgme_widget_message_text").text().trim();
      const date = $(el).find("time").attr("datetime")||"";
      const link = $(el).find(".tgme_widget_message_date").attr("href")||"";
      if (text.length > 20) items.push({ title: text.slice(0,200), description: text, link, date, source: `@${m[1]}` });
    });
    return items.reverse();
  }
}
