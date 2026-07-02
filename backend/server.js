const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { URL } = require("node:url");
const { DatabaseSync } = require("node:sqlite");

const PORT = Number(process.env.PORT || 5173);
const ROOT = path.join(__dirname, "..", "frontend");
const DATA_DIR = path.join(__dirname, "..", "data");
const DB_PATH = path.join(DATA_DIR, "novels.sqlite");

fs.mkdirSync(DATA_DIR, { recursive: true });

const db = new DatabaseSync(DB_PATH);
db.exec(`
  PRAGMA foreign_keys = ON;

  CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL DEFAULT '待补充',
    platform TEXT NOT NULL DEFAULT '待补充',
    summary TEXT NOT NULL DEFAULT '',
    official_url TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '想看',
    rating REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, author)
  );

  CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('official', 'user', 'community')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, type)
  );

  CREATE TABLE IF NOT EXISTS book_tags (
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    weight INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY(book_id, tag_id)
  );

  CREATE TABLE IF NOT EXISTS import_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS import_books (
    import_id INTEGER NOT NULL REFERENCES import_batches(id) ON DELETE CASCADE,
    book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    PRIMARY KEY(import_id, book_id)
  );

  CREATE TABLE IF NOT EXISTS recommend_edges (
    book_a_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    book_b_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    weight INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY(book_a_id, book_b_id),
    CHECK(book_a_id < book_b_id)
  );
`);

seedDatabase();

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host}`);

    if (url.pathname.startsWith("/api/")) {
      await handleApi(req, res, url);
      return;
    }

    serveStatic(res, url.pathname);
  } catch (error) {
    sendJson(res, 500, { error: error.message || "服务器错误" });
  }
});

server.listen(PORT, () => {
  console.log(`书荒雷达已启动：http://localhost:${PORT}`);
});

async function handleApi(req, res, url) {
  if (req.method === "GET" && url.pathname === "/api/books") {
    sendJson(res, 200, { books: searchBooks(url.searchParams) });
    return;
  }

  if (req.method === "GET" && url.pathname === "/api/tags") {
    sendJson(res, 200, { tags: listTags(url.searchParams) });
    return;
  }

  const similarMatch = url.pathname.match(/^\/api\/books\/(\d+)\/similar$/);
  if (req.method === "GET" && similarMatch) {
    sendJson(res, 200, { books: similarBooks(Number(similarMatch[1])) });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/books") {
    const body = await readJson(req);
    const bookId = upsertBook({
      title: body.title,
      author: body.author,
      platform: body.platform,
      summary: body.summary,
      officialUrl: body.officialUrl,
      status: body.status,
      rating: body.rating,
    });
    addTags(bookId, body.officialTags || [], "official");
    addTags(bookId, body.userTags || [], "user");
    sendJson(res, 201, { book: getBook(bookId) });
    return;
  }

  if (req.method === "POST" && url.pathname === "/api/import/text") {
    const body = await readJson(req);
    sendJson(res, 200, importText(body.text || ""));
    return;
  }

  sendJson(res, 404, { error: "没有这个接口" });
}

function searchBooks(params) {
  const q = normalize(params.get("q"));
  const platform = normalize(params.get("platform"));
  const status = normalize(params.get("status"));
  const tagType = normalize(params.get("tagType"));
  const tags = splitTags(params.get("tags")).map(normalize);
  const sort = params.get("sort") || "match";

  const rows = db.prepare(`
    SELECT
      b.*,
      COALESCE(GROUP_CONCAT(t.name || ':' || t.type || ':' || bt.weight, '|'), '') AS tag_blob
    FROM books b
    LEFT JOIN book_tags bt ON bt.book_id = b.id
    LEFT JOIN tags t ON t.id = bt.tag_id
    GROUP BY b.id
  `).all();

  return rows
    .map(hydrateBook)
    .map((book) => ({ book, score: scoreBook(book, q, tags, tagType) }))
    .filter(({ book, score }) => {
      if (platform && !normalize(book.platform).includes(platform)) return false;
      if (status && normalize(book.status) !== status) return false;
      if ((q || tags.length) && score <= 0) return false;
      return true;
    })
    .sort((left, right) => {
      if (sort === "rating") return right.book.rating - left.book.rating;
      if (sort === "recent") return right.book.id - left.book.id;
      return right.score - left.score || right.book.rating - left.book.rating || right.book.id - left.book.id;
    })
    .map(({ book }) => book);
}

function similarBooks(bookId) {
  const rows = db.prepare(`
    SELECT b.*, e.weight AS relation_weight,
      COALESCE(GROUP_CONCAT(t.name || ':' || t.type || ':' || bt.weight, '|'), '') AS tag_blob
    FROM recommend_edges e
    JOIN books b ON b.id = CASE WHEN e.book_a_id = ? THEN e.book_b_id ELSE e.book_a_id END
    LEFT JOIN book_tags bt ON bt.book_id = b.id
    LEFT JOIN tags t ON t.id = bt.tag_id
    WHERE e.book_a_id = ? OR e.book_b_id = ?
    GROUP BY b.id, e.weight
    ORDER BY e.weight DESC, b.rating DESC, b.id DESC
    LIMIT 20
  `).all(bookId, bookId, bookId);

  return rows.map((row) => ({
    ...hydrateBook(row),
    reason: `共同推荐强度 ${row.relation_weight}`,
    relationWeight: row.relation_weight,
  }));
}

function listTags(params) {
  const type = normalize(params.get("type"));
  const q = normalize(params.get("q"));
  return db.prepare(`
    SELECT t.id, t.name, t.type, COUNT(bt.book_id) AS bookCount, COALESCE(SUM(bt.weight), 0) AS weight
    FROM tags t
    LEFT JOIN book_tags bt ON bt.tag_id = t.id
    GROUP BY t.id
    ORDER BY weight DESC, bookCount DESC, t.name ASC
  `).all().filter((tag) => {
    if (type && tag.type !== type) return false;
    if (q && !normalize(tag.name).includes(q)) return false;
    return true;
  });
}

function importText(text) {
  const cleanText = text.trim();
  if (!cleanText) return { imported: 0, skipped: true, reason: "文本为空" };

  const hash = crypto.createHash("sha256").update(cleanText).digest("hex");
  const existing = db.prepare("SELECT id FROM import_batches WHERE content_hash = ?").get(hash);
  if (existing) {
    return { imported: 0, skipped: true, reason: "这段文本已经导入过" };
  }

  const parsedBooks = parseBooksFromText(cleanText);
  if (!parsedBooks.length) {
    return { imported: 0, skipped: true, reason: "没有识别到《书名》" };
  }

  const importId = db.prepare("INSERT INTO import_batches (type, content_hash) VALUES ('text', ?)").run(hash).lastInsertRowid;
  const bookIds = [];

  parsedBooks.forEach((book) => {
    const bookId = upsertBook(book);
    addTags(bookId, book.officialTags || [], "official");
    addTags(bookId, book.userTags || [], "user");
    addTags(bookId, book.communityTags || [], "community");
    db.prepare("INSERT OR IGNORE INTO import_books (import_id, book_id) VALUES (?, ?)").run(importId, bookId);
    bookIds.push(bookId);
  });

  addRecommendationEdges(bookIds);
  return { imported: bookIds.length, books: bookIds.map(getBook) };
}

function parseBooksFromText(text) {
  const matches = [...text.matchAll(/《([^》]{1,80})》/g)];
  if (!matches.length) return [];

  return matches.map((match, index) => {
    const start = match.index || 0;
    const end = matches[index + 1]?.index || text.length;
    const block = text.slice(start, end);
    const tags = extractLine(block, "标签");
    const officialTags = extractLine(block, "官方标签");
    const platform = extractLine(block, "平台") || guessPlatform(block);

    return {
      title: match[1].trim(),
      author: extractLine(block, "作者") || "待补充",
      platform: platform || "待补充",
      summary: extractLine(block, "简介") || extractLine(block, "推荐语") || block.replace(match[0], "").trim(),
      officialUrl: extractUrl(block),
      status: "想看",
      rating: 0,
      officialTags: splitTags(officialTags),
      userTags: [],
      communityTags: splitTags(tags || extractHashTags(block).join(",")),
    };
  });
}

function extractLine(text, label) {
  const pattern = new RegExp(`${label}\\s*[:：]\\s*([^\\n]+)`);
  return text.match(pattern)?.[1]?.trim() || "";
}

function extractHashTags(text) {
  return [...text.matchAll(/#([\p{Script=Han}\w-]+)/gu)].map((match) => match[1]);
}

function extractUrl(text) {
  return text.match(/https?:\/\/\S+/)?.[0] || "";
}

function guessPlatform(text) {
  const platforms = ["晋江", "起点", "番茄", "长佩", "豆瓣阅读", "知乎盐选", "刺猬猫"];
  return platforms.find((platform) => text.includes(platform)) || "";
}

function upsertBook(input) {
  const book = {
    title: String(input.title || "").replace(/[《》]/g, "").trim(),
    author: String(input.author || "待补充").trim() || "待补充",
    platform: String(input.platform || "待补充").trim() || "待补充",
    summary: String(input.summary || "").trim(),
    officialUrl: String(input.officialUrl || "").trim(),
    status: String(input.status || "想看").trim() || "想看",
    rating: Number(input.rating || 0),
  };

  if (!book.title) throw new Error("书名不能为空");

  db.prepare(`
    INSERT INTO books (title, author, platform, summary, official_url, status, rating)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(title, author) DO UPDATE SET
      platform = CASE WHEN excluded.platform != '待补充' THEN excluded.platform ELSE books.platform END,
      summary = CASE WHEN excluded.summary != '' THEN excluded.summary ELSE books.summary END,
      official_url = CASE WHEN excluded.official_url != '' THEN excluded.official_url ELSE books.official_url END,
      status = CASE WHEN books.status = '想看' THEN excluded.status ELSE books.status END,
      rating = CASE WHEN excluded.rating > 0 THEN excluded.rating ELSE books.rating END,
      updated_at = CURRENT_TIMESTAMP
  `).run(book.title, book.author, book.platform, book.summary, book.officialUrl, book.status, book.rating);

  return db.prepare("SELECT id FROM books WHERE title = ? AND author = ?").get(book.title, book.author).id;
}

function addTags(bookId, tags, type) {
  splitTags(tags.join ? tags.join(",") : tags).forEach((tag) => {
    const tagId = upsertTag(tag, type);
    db.prepare(`
      INSERT INTO book_tags (book_id, tag_id, weight)
      VALUES (?, ?, 1)
      ON CONFLICT(book_id, tag_id) DO UPDATE SET weight = weight + 1
    `).run(bookId, tagId);
  });
}

function upsertTag(name, type) {
  const cleanName = String(name || "").trim();
  if (!cleanName) return null;
  db.prepare("INSERT OR IGNORE INTO tags (name, type) VALUES (?, ?)").run(cleanName, type);
  return db.prepare("SELECT id FROM tags WHERE name = ? AND type = ?").get(cleanName, type).id;
}

function addRecommendationEdges(bookIds) {
  const uniqueIds = [...new Set(bookIds)].sort((a, b) => a - b);
  for (let i = 0; i < uniqueIds.length; i += 1) {
    for (let j = i + 1; j < uniqueIds.length; j += 1) {
      db.prepare(`
        INSERT INTO recommend_edges (book_a_id, book_b_id, weight)
        VALUES (?, ?, 1)
        ON CONFLICT(book_a_id, book_b_id) DO UPDATE SET weight = weight + 1
      `).run(uniqueIds[i], uniqueIds[j]);
    }
  }
}

function getBook(bookId) {
  const row = db.prepare(`
    SELECT b.*, COALESCE(GROUP_CONCAT(t.name || ':' || t.type || ':' || bt.weight, '|'), '') AS tag_blob
    FROM books b
    LEFT JOIN book_tags bt ON bt.book_id = b.id
    LEFT JOIN tags t ON t.id = bt.tag_id
    WHERE b.id = ?
    GROUP BY b.id
  `).get(bookId);
  return hydrateBook(row);
}

function hydrateBook(row) {
  const tags = { official: [], user: [], community: [] };
  String(row.tag_blob || "").split("|").filter(Boolean).forEach((item) => {
    const [name, type, weight] = item.split(":");
    if (tags[type]) tags[type].push({ name, weight: Number(weight || 1) });
  });

  return {
    id: row.id,
    title: row.title,
    author: row.author,
    platform: row.platform,
    summary: row.summary,
    officialUrl: row.official_url,
    status: row.status,
    rating: row.rating,
    tags,
  };
}

function scoreBook(book, q, queryTags, tagType) {
  const tagEntries = [...book.tags.official, ...book.tags.user, ...book.tags.community];
  const tagNames = tagEntries.map((tag) => normalize(tag.name));
  const text = normalize([book.title, book.author, book.platform, book.summary, tagNames.join(" ")].join(" "));
  let score = 0;

  splitTags(q).map(normalize).forEach((part) => {
    if (book.tags.official.some((tag) => normalize(tag.name) === part)) score += 6;
    else if (book.tags.user.some((tag) => normalize(tag.name) === part)) score += 4;
    else if (book.tags.community.some((tag) => normalize(tag.name) === part)) score += 3;
    else if (normalize(book.title).includes(part)) score += 5;
    else if (text.includes(part)) score += 1;
  });

  queryTags.forEach((tag) => {
    const candidates = tagType ? book.tags[tagType] || [] : tagEntries;
    if (candidates.some((candidate) => normalize(candidate.name) === tag)) score += 5;
  });

  return score;
}

function splitTags(value) {
  return String(value || "")
    .split(/[,，、\s]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function sendJson(res, status, payload) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
}

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(new Error("JSON 格式不正确"));
      }
    });
  });
}

function serveStatic(res, pathname) {
  const safePath = pathname === "/" ? "index.html" : pathname.replace(/^\/+/, "");
  const filePath = path.resolve(ROOT, safePath);
  if (!filePath.startsWith(ROOT)) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    res.writeHead(404);
    res.end("Not found");
    return;
  }

  const ext = path.extname(filePath);
  const type = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
  }[ext] || "application/octet-stream";

  res.writeHead(200, { "content-type": type });
  fs.createReadStream(filePath).pipe(res);
}

function seedDatabase() {
  const count = db.prepare("SELECT COUNT(*) AS count FROM books").get().count;
  if (count > 0) return;

  const samples = [
    {
      title: "你搁这和我装B呢",
      author: "待补充",
      platform: "待补充",
      summary: "样例条目：用于测试“老实人”“同类推荐”等口味搜索。",
      officialTags: [],
      communityTags: ["bg", "老实人", "同类推荐"],
    },
    {
      title: "老实人，但万人迷",
      author: "待补充",
      platform: "待补充",
      summary: "样例条目：和前一本书共同出现在同一批推书里时，会形成同类推荐关系。",
      officialTags: [],
      communityTags: ["bg", "老实人", "万人迷"],
    },
    {
      title: "稳住别浪",
      author: "跳舞",
      platform: "起点",
      summary: "都市异能，节奏偏爽文，适合测试平台和官方标签筛选。",
      officialTags: ["都市", "异能"],
      communityTags: ["爽文"],
    },
  ];

  const ids = samples.map((sample) => {
    const id = upsertBook(sample);
    addTags(id, sample.officialTags, "official");
    addTags(id, sample.communityTags, "community");
    return id;
  });
  addRecommendationEdges(ids.slice(0, 2));
}
