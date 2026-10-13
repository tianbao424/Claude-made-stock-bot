// 把 dist-demo 里的脚本、样式和 demo/fixtures.json 拼成一个可以直接打开的 HTML 片段：
// dist-demo/preview.html（没有 <html>/<head>/<body>，发布为 Artifact 时会自动套上）。
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const web = new URL("..", import.meta.url).pathname;
const dist = join(web, "dist-demo");
const fixtures = join(web, "demo", "fixtures.json");
if (!existsSync(fixtures)) {
  console.error("缺少 demo/fixtures.json：先在 mistake-mastery 目录下运行 uv run python web/demo/make_fixtures.py");
  process.exit(1);
}
const assets = readdirSync(join(dist, "assets"));
const js = assets.filter((f) => f.endsWith(".js")).map((f) => readFileSync(join(dist, "assets", f), "utf8")).join("\n");
let css = assets.filter((f) => f.endsWith(".css")).map((f) => readFileSync(join(dist, "assets", f), "utf8")).join("\n");
// KaTeX 字体只留 woff2（现代浏览器都支持），去掉 woff/ttf 备份，文件小一半多
css = css.replace(/,url\(data:font\/(woff|ttf);base64,[^)]*\) format\("(woff|truetype)"\)/g, "");

// 内联到 <script> 里的内容不能出现 "</script"：JSON 里把 < 写成 \u003c，脚本里写成 <\/script
const safeJson = (s) => s.replace(/</g, "\\u003c");
// 另外，markdown 库的字符串里有字面的 U+FFFD（替换字符），写成转义形式，免得被当成乱码
const safeJs = (s) => s.replace(/<\/(script)/gi, "<\\/$1").replace(/\uFFFD/g, "\\uFFFD");
const html = [
  "<title>学透预览版</title>",
  `<style>${css}</style>`,
  '<div id="root"></div>',
  `<script type="application/json" id="xt-fixtures">${safeJson(readFileSync(fixtures, "utf8"))}</script>`,
  `<script type="module">${safeJs(js)}</script>`,
  "",
].join("\n");
const out = join(dist, "preview.html");
writeFileSync(out, html);
console.log(`wrote ${out} (${(html.length / 1e6).toFixed(1)} MB)`);
