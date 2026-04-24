const http = require("http");
const fs = require("fs");
const path = require("path");

const baseDir = process.argv[2];
const port = Number(process.argv[3] || 8765);

if (!baseDir) {
  console.error("Missing base directory");
  process.exit(1);
}

const server = http.createServer((req, res) => {
  const relPath = decodeURIComponent((req.url || "/").split("?")[0]).replace(/^\/+/, "");
  const target = path.join(baseDir, relPath || "index.html");

  fs.readFile(target, (err, data) => {
    if (err) {
      res.writeHead(404, {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "text/plain; charset=utf-8",
      });
      res.end("not found");
      return;
    }

    const ext = path.extname(target).toLowerCase();
    const contentType =
      ext === ".js"
        ? "application/javascript; charset=utf-8"
        : "text/plain; charset=utf-8";

    res.writeHead(200, {
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
      "Content-Type": contentType,
    });
    res.end(data);
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`serving ${baseDir} on http://127.0.0.1:${port}`);
});
