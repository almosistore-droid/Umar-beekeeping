// One-off codemod: wrap every Russian UI text in src/ with tr() from src/i18n.
//   node scripts/i18n-codemod.mjs [--dry]
// - string literals / no-substitution templates with Cyrillic  →  tr("…")
// - template literals with Cyrillic                            →  tr("…{0}…{1}…", a, b)
// - JSX text, merged with neighbouring simple {expressions}     →  {tr("Сумма: {0} кг", sum)}
// Skips: tests, i18n itself, imports, object keys, type positions, calls that are already tr(…).
import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const SRC = path.resolve('src')
const CYR = /[А-Яа-яЁё]/
const dry = process.argv.includes('--dry')

function files(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) return ['test', 'i18n'].includes(e.name) ? [] : files(p)
    return /\.(ts|tsx)$/.test(e.name) && !e.name.endsWith('.d.ts') ? [p] : []
  })
}

const q = (s) => JSON.stringify(s)

function isTrCall(node) {
  return node && ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'tr'
}

function containsJsx(node) {
  let found = false
  const visit = (n) => {
    if (found) return
    if (ts.isJsxElement(n) || ts.isJsxSelfClosingElement(n) || ts.isJsxFragment(n)) { found = true; return }
    ts.forEachChild(n, visit)
  }
  visit(node)
  return found
}

/** JSX whitespace rules: whitespace with a line break is dropped, lines are trimmed and joined by a space. */
function jsxTextValue(raw) {
  const lines = raw.split(/\r\n|\n|\r/)
  if (lines.length === 1) return raw
  const out = []
  lines.forEach((line, i) => {
    let l = line
    if (i > 0) l = l.trimStart()
    if (i < lines.length - 1) l = l.trimEnd()
    if (l) out.push(l)
  })
  return out.join(' ')
}

function processFile(file) {
  const text = fs.readFileSync(file, 'utf8')
  if (!CYR.test(text)) return { changed: false, keys: [] }
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
  const keys = []

  // Rewrites `node` and returns its new source text (recursively applied to children).
  function rewrite(node) {
    const edits = []
    collect(node, edits)
    let out = text.slice(node.getStart(sf), node.getEnd())
    const base = node.getStart(sf)
    edits.sort((a, b) => b.start - a.start)
    for (const e of edits) out = out.slice(0, e.start - base) + e.text + out.slice(e.end - base)
    return out
  }

  function simpleExpr(expr) {
    return expr && !containsJsx(expr) && (ts.isIdentifier(expr) || ts.isPropertyAccessExpression(expr) || ts.isElementAccessExpression(expr)
      || ts.isCallExpression(expr) || ts.isStringLiteral(expr) || ts.isNumericLiteral(expr) || ts.isTemplateExpression(expr) || ts.isNoSubstitutionTemplateLiteral(expr))
  }

  function templateCall(node) {
    let key = node.head.text
    const args = []
    node.templateSpans.forEach((span, i) => {
      key += `{${i}}` + span.literal.text
      args.push(rewrite(span.expression))
    })
    keys.push(key)
    return `tr(${q(key)}${args.map((a) => `, ${a}`).join('')})`
  }

  function collect(node, edits) {
    // JSX children runs
    if (ts.isJsxElement(node) || ts.isJsxFragment(node)) {
      const kids = node.children
      let i = 0
      while (i < kids.length) {
        const k = kids[i]
        const isText = ts.isJsxText(k)
        const isSimpleExpr = ts.isJsxExpression(k) && k.expression && simpleExpr(k.expression)
        if (isText || isSimpleExpr) {
          let j = i
          while (j < kids.length && (ts.isJsxText(kids[j]) || (ts.isJsxExpression(kids[j]) && kids[j].expression && simpleExpr(kids[j].expression)))) j++
          const run = kids.slice(i, j)
          const hasCyr = run.some((c) => ts.isJsxText(c) && CYR.test(c.text))
          if (hasCyr) {
            let key = ''
            const args = []
            for (const c of run) {
              if (ts.isJsxText(c)) key += jsxTextValue(c.text)
              else { key += `{${args.length}}`; args.push(rewrite(c.expression)) }
            }
            const lead = key.length - key.trimStart().length
            const trail = key.length - key.trimEnd().length
            const core = key.trim()
            // keep surrounding same-line spaces outside the translated text
            const pre = key.slice(0, lead), post = trail ? key.slice(key.length - trail) : ''
            keys.push(core)
            const call = `{tr(${q(core)}${args.map((a) => `, ${a}`).join('')})}`
            const start = run[0].getStart(sf, true) === run[0].pos ? run[0].pos : run[0].pos
            edits.push({ start, end: run[run.length - 1].getEnd(), text: (pre ? `{${q(pre)}}` : '') + call + (post ? `{${q(post)}}` : '') })
          } else {
            for (const c of run) if (!ts.isJsxText(c)) collect(c, edits)
          }
          i = j
          continue
        }
        collect(k, edits)
        i++
      }
      if (ts.isJsxElement(node)) { collect(node.openingElement, edits); collect(node.closingElement, edits) }
      return
    }

    if ((ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) && CYR.test(node.text)) {
      const p = node.parent
      if (ts.isImportDeclaration(p) || ts.isExportDeclaration(p) || ts.isLiteralTypeNode(p)) return
      if ((ts.isPropertyAssignment(p) || ts.isPropertySignature(p)) && p.name === node) return
      if (isTrCall(p) && p.arguments[0] === node) return
      keys.push(node.text)
      if (ts.isJsxAttribute(p)) edits.push({ start: node.getStart(sf), end: node.getEnd(), text: `{tr(${q(node.text)})}` })
      else edits.push({ start: node.getStart(sf), end: node.getEnd(), text: `tr(${q(node.text)})` })
      return
    }
    if (ts.isTemplateExpression(node)) {
      const parts = [node.head.text, ...node.templateSpans.map((s) => s.literal.text)]
      if (parts.some((p) => CYR.test(p))) {
        if (isTrCall(node.parent)) return
        edits.push({ start: node.getStart(sf), end: node.getEnd(), text: templateCall(node) })
        return
      }
    }
    ts.forEachChild(node, (c) => collect(c, edits))
  }

  const edits = []
  ts.forEachChild(sf, (c) => collect(c, edits))
  if (!edits.length) return { changed: false, keys }
  edits.sort((a, b) => b.start - a.start)
  let out = text
  for (const e of edits) out = out.slice(0, e.start) + e.text + out.slice(e.end)
  if (!/import \{[^}]*\btr\b[^}]*\} from '[./]*i18n'/.test(out)) {
    let rel = path.relative(path.dirname(file), path.join(SRC, 'i18n')).replace(/\\/g, '/')
    if (!rel.startsWith('.')) rel = './' + rel
    // after the last import declaration of the ORIGINAL file (edits never touch imports, which come first)
    const imports = sf.statements.filter((st) => ts.isImportDeclaration(st))
    if (imports.length) {
      const at = imports[imports.length - 1].getEnd()
      out = out.slice(0, at) + `\nimport { tr } from '${rel}'` + out.slice(at)
    } else {
      out = `import { tr } from '${rel}'\n\n` + out
    }
  }
  if (!dry) fs.writeFileSync(file, out)
  return { changed: true, keys }
}

const all = new Set()
let changed = 0
for (const f of files(SRC)) {
  const r = processFile(f)
  if (r.changed) changed++
  r.keys.forEach((k) => all.add(k))
}
console.log(`files changed: ${changed}, texts: ${all.size}`)
fs.writeFileSync('scripts/i18n-keys.json', JSON.stringify([...all].sort(), null, 1))
