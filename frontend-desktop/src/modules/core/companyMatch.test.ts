import {describe, it, expect} from 'vitest'
import {companyMatches} from './companyMatch'
import cases from '../../../../tests/fixtures/company-name-matches.json'

describe('company name candidate matching', () => {
  it.each(cases)('$left / $right -> $match', ({left, right, match}) => {
    expect(companyMatches(left, right)).toBe(match)
    expect(companyMatches(right, left)).toBe(match)
  })
})
