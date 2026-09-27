export type Row = Record<string, any>
export function flatten(rows: Row[]): Row[] { return rows.flatMap(row => [row, ...flatten(row.children || [])]) }
export function permittedParents(rows: Row[], id?: number): Row[] {
  const flat = flatten(rows), excluded = new Set<number>(id ? [id] : [])
  let changed = true
  while (changed) { changed = false; for (const row of flat) if (excluded.has(row.pid) && !excluded.has(row.id)) { excluded.add(row.id); changed = true } }
  return flat.filter(row => !excluded.has(row.id))
}
export function userPayload(form: Row): Row { const out = { ...form }; delete out.children; if (!out.password || /^\*+$/.test(out.password)) delete out.password; return out }
export function editablePayload(form: Row): Row { const out = { ...form }; delete out.children; return out }
export function passwordError(old: string, next: string, confirm: string): string { return !old ? '请输入原密码' : next.length < 6 ? '新密码至少6位' : next !== confirm ? '两次密码不一致' : '' }
export function backupPayload(form: Row, hadPassword: boolean): Row { return { ...form, mail_pass: form.mail_pass || (hadPassword ? '******' : '') } }
export function safeSelection(current: Array<number|string>, options: Row[]): number[] { const allowed = new Set(flatten(options).map(x => Number(x.id))); return current.map(Number).filter(x => allowed.has(x)) }
