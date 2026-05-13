import express from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import path from "path";
import { fileURLToPath } from "url";

const app = express();
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const port = Number(process.env.PORT || 3000);
const apiTarget = process.env.API_BASE_URL || "http://dashboard-api:8000";

app.use(
  "/api",
  createProxyMiddleware({
    target: apiTarget,
    changeOrigin: true,
    pathRewrite: { "^/api": "" },
  })
);

app.use(express.static(path.join(__dirname, "frontend")));
app.get("*", (_req, res) => {
  res.sendFile(path.join(__dirname, "frontend", "index.html"));
});

app.listen(port, () => {
  console.log(`Dashboard frontend on ${port}, API -> ${apiTarget}`);
});
