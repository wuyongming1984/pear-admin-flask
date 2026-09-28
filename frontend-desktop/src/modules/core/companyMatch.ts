// Keep this normalization aligned with pear_admin.invoice_links.company_key.
export function companyKey(value: unknown): string {
  return String(value || '').normalize('NFKC').toLowerCase().replace(/\s/g, '')
    .replace(/(公司|中心|商行|经营部|工作室)(?:\([^()]*\))+[。.,，]*$/u, '$1')
    .replace(/[^\p{L}\p{N}]/gu, '')
}

export function companyMatches(left: unknown, right: unknown): boolean {
  const a = companyKey(left), b = companyKey(right)
  const generic = /^(?:有限责任公司|有限公司|公司|集团|中心|商行|分公司|经营部|工作室)+$/u
  if (!a || !b || generic.test(a) || generic.test(b)) return false
  if (a === b) return true
  return Math.min([...a].length, [...b].length) >= 4 && (a.includes(b) || b.includes(a))
}
