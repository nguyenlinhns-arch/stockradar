// Build-only dependency; no extra SDK or runtime is shipped to visitors.
const fs = require('node:fs');
const path = require('node:path');
const {minify} = require('terser');
(async () => {
  const root = path.resolve(process.argv[2] || '.pages-site');
  let before = 0, after = 0;
  for (const name of ['conversion-v3.js', 'ai-center.js', 'auth-state-v2.js', 'home-workspace-v2.js', 'auth.js', 'app.js']) {
    const file = path.join(root, 'assets', name), source = fs.readFileSync(file, 'utf8');
    const result = await minify(source, {ecma: 2020, compress: false, mangle: false, format: {comments: false}});
    if (!result.code) throw new Error('Empty minifier result: ' + name);
    before += Buffer.byteLength(source); after += Buffer.byteLength(result.code);
    fs.writeFileSync(file, result.code + '\n');
  }
  console.log(JSON.stringify({funnel_minify: true, before, after}));
})().catch(error => {console.error(error.message); process.exitCode = 1;});
