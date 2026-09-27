import type {Row} from './model'

export const contactName = (value: unknown) => String(value ?? '').trim()
export const contactNames = (suppliers: Row[]) => [...new Set(suppliers.map(s => contactName(s.contact_person)).filter(Boolean))]
export function suppliersForContact(suppliers: Row[], contact: unknown): Row[] {
  const name = contactName(contact)
  return name ? suppliers.filter(s => contactName(s.contact_person) === name) : []
}

export function changeOrderContact(record: Row, suppliers: Row[]) {
  record.supplier_contact_person = contactName(record.supplier_contact_person)
  const matches = suppliersForContact(suppliers, record.supplier_contact_person)
  const supplier = matches.find(s => s.id === record.supplier_id) || (matches.length === 1 ? matches[0] : undefined)
  record.supplier_id = supplier?.id
  record.contact_phone = supplier?.phone || ''
}

export function changeOrderSupplier(record: Row, suppliers: Row[]) {
  const supplier = suppliersForContact(suppliers, record.supplier_contact_person).find(s => s.id === record.supplier_id)
  record.supplier_id = supplier?.id
  record.contact_phone = supplier?.phone || ''
}
