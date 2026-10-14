/// <reference types="node" />
import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'
import { afterEach, describe, expect, it } from 'vitest'
import tg from '../i18n/tg.json'
import { adoptServerLang, detectLang, setLangForTests, switchLang, tr } from '../i18n'

const SRC = path.resolve(__dirname, '..')
const CYR = /[А-Яа-яЁё]/

function sourceFiles(dir: string): string[] {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((e) => {
    const p = path.join(dir, e.name)
    if (e.isDirectory()) return ['test', 'i18n'].includes(e.name) ? [] : sourceFiles(p)
    return /\.(ts|tsx)$/.test(e.name) && !e.name.endsWith('.d.ts') ? [p] : []
  })
}

/** Every tr("…") key in the app, and every Russian text that is NOT inside tr(…). */
function scan() {
  const keys = new Set<string>()
  const untranslated: string[] = []
  for (const file of sourceFiles(SRC)) {
    const text = fs.readFileSync(file, 'utf8')
    const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
    const ignored = (n: ts.Node) => {
      const line = sf.getLineAndCharacterOfPosition(n.getStart(sf)).line
      return text.split('\n')[line].includes('i18n-ignore')
    }
    const where = (n: ts.Node) => `${path.relative(SRC, file)}:${sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1}`
    const visit = (n: ts.Node) => {
      if (ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === 'tr') {
        const first = n.arguments[0]
        if (first && (ts.isStringLiteral(first) || ts.isNoSubstitutionTemplateLiteral(first))) keys.add(first.text)
        n.arguments.slice(1).forEach(visit)
        return
      }
      if ((ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) && CYR.test(n.text) && !ts.isImportDeclaration(n.parent) && !ignored(n)) {
        untranslated.push(`${where(n)}  "${n.text}"`)
      }
      if (ts.isJsxText(n) && CYR.test(n.text) && !ignored(n)) untranslated.push(`${where(n)}  ${n.text.trim()}`)
      if (ts.isTemplateExpression(n) && [n.head.text, ...n.templateSpans.map((s) => s.literal.text)].some((p) => CYR.test(p)) && !ignored(n)) {
        untranslated.push(`${where(n)}  \`${n.getText(sf)}\``)
      }
      ts.forEachChild(n, visit)
    }
    visit(sf)
  }
  return { keys, untranslated }
}

describe('Тоҷикӣ coverage', () => {
  const { keys, untranslated } = scan()

  it('every Russian UI text goes through tr()', () => {
    expect(untranslated).toEqual([])
  })

  it('every tr() text has a Tajik translation', () => {
    const catalog = tg as Record<string, string>
    expect([...keys].filter((k) => !catalog[k])).toEqual([])
  })

  it('translations keep placeholders and edge spaces', () => {
    const catalog = tg as Record<string, string>
    const ph = (s: string) => (s.match(/\{\d+\}/g) ?? []).sort().join()
    const broken = Object.entries(catalog).filter(([ru, t]) => ph(ru) !== ph(t) || /^\s/.test(ru) !== /^\s/.test(t) || /\s$/.test(ru) !== /\s$/.test(t))
    expect(broken).toEqual([])
  })
})

describe('tr() and language choice', () => {
  afterEach(() => { setLangForTests('ru'); localStorage.clear(); delete window.Telegram })

  it('returns Russian as is and Tajik from the catalog, with placeholders', () => {
    expect(tr('Улей №{0}', 27)).toBe('Улей №27')
    setLangForTests('tg')
    expect(tr('Улей №{0}', 27)).toBe('Қуттии №27')
    expect(tr('Сохранить осмотр')).toBe('Нигоҳ доштани муоина')
    expect(tr('Текст, которого нет в каталоге')).toBe('Текст, которого нет в каталоге')
    expect(tr('Улей №{0}', null)).toBe('Қуттии №')
  })

  it('follows Telegram language unless a choice is saved', () => {
    window.Telegram = { WebApp: { initDataUnsafe: { user: { id: 1, language_code: 'tg' } } } } as never
    expect(detectLang()).toBe('tg')
    window.Telegram = { WebApp: { initDataUnsafe: { user: { id: 1, language_code: 'en' } } } } as never
    expect(detectLang()).toBe('ru')
    localStorage.setItem('fayzi-umar.lang', 'tg')
    expect(detectLang()).toBe('tg')
  })

  it('switching saves the choice and reloads; a server choice is adopted only when nothing is saved locally', () => {
    let reloads = 0
    adoptServerLang('tg', () => reloads++)
    expect(reloads).toBe(1)
    expect(localStorage.getItem('fayzi-umar.lang')).toBe('tg')
    adoptServerLang('ru', () => reloads++)  // device already has a choice
    expect(reloads).toBe(1)
    switchLang('ru', () => reloads++)
    expect(reloads).toBe(2)
    expect(localStorage.getItem('fayzi-umar.lang')).toBe('ru')
  })
})
