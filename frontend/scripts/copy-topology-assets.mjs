// Copies the topology-ui image assets into public/ so the renderer can reference them via
// assetRoot "/topology-ui/images". Runs in `predev` and `prebuild`.
import { cpSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(root, "node_modules/@couchbaselabs/topology-ui/images");
const target = resolve(root, "public/topology-ui/images");

if (!existsSync(source)) {
  console.error(`topology-ui images not found at ${source}; run npm install first`);
  process.exit(1);
}
mkdirSync(target, { recursive: true });
cpSync(source, target, { recursive: true });
console.log(`copied topology-ui images -> ${target}`);
