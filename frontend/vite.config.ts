import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const repoName = process.env.REPO_NAME ?? process.env.GITHUB_REPOSITORY?.split("/")[1];

export default defineConfig({
  plugins: [react()],
  base: repoName ? `/${repoName}/` : "/",
});
