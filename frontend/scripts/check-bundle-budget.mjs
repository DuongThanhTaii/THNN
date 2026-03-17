import fs from "node:fs";
import path from "node:path";

const distAssets = path.resolve("dist/assets");
const jsBudgetBytes = 270 * 1024;
const cssBudgetBytes = 12 * 1024;

if (!fs.existsSync(distAssets)) {
  console.error("dist/assets not found. Run npm run build first.");
  process.exit(1);
}

const files = fs.readdirSync(distAssets);
const jsFiles = files.filter((name) => name.endsWith(".js"));
const cssFiles = files.filter((name) => name.endsWith(".css"));

let maxJs = 0;
let maxCss = 0;

for (const file of jsFiles) {
  const size = fs.statSync(path.join(distAssets, file)).size;
  maxJs = Math.max(maxJs, size);
}

for (const file of cssFiles) {
  const size = fs.statSync(path.join(distAssets, file)).size;
  maxCss = Math.max(maxCss, size);
}

console.log(`Largest JS bundle: ${maxJs} bytes (budget ${jsBudgetBytes})`);
console.log(`Largest CSS bundle: ${maxCss} bytes (budget ${cssBudgetBytes})`);

if (maxJs > jsBudgetBytes || maxCss > cssBudgetBytes) {
  console.error("Bundle budget exceeded.");
  process.exit(1);
}

console.log("Bundle budget check passed.");
