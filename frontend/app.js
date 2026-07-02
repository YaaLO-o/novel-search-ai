let sortMode = "match";

const searchInput = document.querySelector("#searchInput");
const platformFilter = document.querySelector("#platformFilter");
const statusFilter = document.querySelector("#statusFilter");
const tagCloud = document.querySelector("#tagCloud");
const resultCount = document.querySelector("#resultCount");
const bookGrid = document.querySelector("#bookGrid");
const bookForm = document.querySelector("#bookForm");
const bulkText = document.querySelector("#bulkText");
const importButton = document.querySelector("#importButton");
const importMessage = document.querySelector("#importMessage");
const template = document.querySelector("#bookCardTemplate");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "请求失败");
  return payload;
}

async function loadBooks() {
  const params = new URLSearchParams({
    q: searchInput.value,
    platform: platformFilter.value,
    status: statusFilter.value,
    sort: sortMode,
  });
  return api(`/api/books?${params}`);
}

async function render() {
  const [{ books }, { tags }] = await Promise.all([
    loadBooks(),
    api("/api/tags"),
  ]);
  renderTags(tags);
  renderBooks(books);
}

function renderTags(tags) {
  tagCloud.innerHTML = "";
  tags.slice(0, 24).forEach((tag) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tag-chip tag-${tag.type}`;
    button.textContent = `${tag.name} ${tag.weight}`;
    button.title = tagTypeName(tag.type);
    button.addEventListener("click", () => {
      searchInput.value = tag.name;
      render();
    });
    tagCloud.append(button);
  });
}

function renderBooks(books) {
  resultCount.textContent = `找到 ${books.length} 本`;
  bookGrid.innerHTML = "";

  if (!books.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "没有匹配的书。可以先粘贴一段 Obsidian 推书笔记。";
    bookGrid.append(empty);
    return;
  }

  books.forEach(async (book) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".source").textContent = book.platform || "待补充平台";
    node.querySelector("h3").textContent = book.title;
    node.querySelector(".rating").textContent = book.rating ? Number(book.rating).toFixed(1) : "新";
    node.querySelector(".meta").textContent = `作者：${book.author || "待补充"} · 状态：${book.status || "想看"}`;
    node.querySelector(".summary").textContent = book.summary || "还没有简介，可以之后补。";

    renderTagBlock(node.querySelector(".official-tags"), "官方", book.tags.official);
    renderTagBlock(node.querySelector(".user-tags"), "我的", book.tags.user);
    renderTagBlock(node.querySelector(".community-tags"), "网友常提", book.tags.community);

    const link = node.querySelector(".book-link");
    if (book.officialUrl) {
      link.href = book.officialUrl;
    } else {
      link.removeAttribute("href");
      link.textContent = "暂无链接";
    }

    bookGrid.append(node);
    renderSimilar(book.id, node.querySelector(".similar"));
  });
}

function renderTagBlock(container, label, tags) {
  container.innerHTML = "";
  if (!tags.length) return;

  const title = document.createElement("strong");
  title.textContent = `${label}：`;
  container.append(title);
  tags.forEach((tag) => {
    const span = document.createElement("span");
    span.textContent = tag.name;
    container.append(span);
  });
}

async function renderSimilar(bookId, container) {
  const { books } = await api(`/api/books/${bookId}/similar`);
  if (!books.length) return;

  container.textContent = "";
  const title = document.createElement("strong");
  title.textContent = "同类：";
  container.append(title);
  books.slice(0, 3).forEach((book) => {
    const span = document.createElement("span");
    span.textContent = `${book.title}（${book.reason}）`;
    container.append(span);
  });
}

function tagTypeName(type) {
  return {
    official: "官方标签",
    user: "我的标签",
    community: "网友高频词",
  }[type] || "标签";
}

bookForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(bookForm);
  await api("/api/books", {
    method: "POST",
    body: JSON.stringify({
      title: formData.get("title"),
      author: formData.get("author"),
      platform: formData.get("platform"),
      summary: formData.get("summary"),
      officialUrl: formData.get("officialUrl"),
      status: formData.get("status"),
      officialTags: splitTags(formData.get("officialTags")),
      userTags: splitTags(formData.get("userTags")),
    }),
  });
  bookForm.reset();
  render();
});

importButton.addEventListener("click", async () => {
  importMessage.textContent = "";
  const text = bulkText.value.trim();
  if (!text) return;

  const result = await api("/api/import/text", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
  importMessage.textContent = result.skipped ? result.reason : `已导入 ${result.imported} 本`;
  if (!result.skipped) bulkText.value = "";
  render();
});

document.querySelectorAll(".sort-button").forEach((button) => {
  button.addEventListener("click", () => {
    sortMode = button.dataset.sort;
    document.querySelectorAll(".sort-button").forEach((item) => item.classList.toggle("active", item === button));
    render();
  });
});

[searchInput, platformFilter, statusFilter].forEach((control) => {
  control.addEventListener("input", render);
});

function splitTags(value) {
  return String(value || "")
    .split(/[,，、\s]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);
}

render();
