import assert from 'node:assert/strict'
import { test } from 'vitest'
import { permittedParents, userPayload, backupPayload, passwordError, safeSelection } from '../helpers'
test('parent choices exclude entire subtree, retaining unrelated branches',()=>{
 const rows=[{id:1,children:[{id:2,pid:1,children:[{id:3,pid:2}]}]},{id:4,pid:null}]
 assert.deepEqual(permittedParents(rows,1).map(x=>x.id),[4])
 assert.deepEqual(permittedParents(rows,2).map(x=>x.id),[1,4])
})
test('empty and masked user passwords preserve existing credentials and hidden values',()=>{
 for(const password of ['', '******'])assert.deepEqual(userPayload({id:4,password,email:'a',department_id:19}),{id:4,email:'a',department_id:19})
 assert.equal(userPayload({password:'new value'}).password,'new value')
})
test('backup password is preserved using server mask only when already configured',()=>{
 assert.equal(backupPayload({mail_pass:''},true).mail_pass,'******')
 assert.equal(backupPayload({mail_pass:''},false).mail_pass,'')
 assert.equal(backupPayload({mail_pass:'new'},true).mail_pass,'new')
})
test('grant selection never automatically includes available but unassigned roles',()=>{
 assert.deepEqual(safeSelection([2],[{id:1},{id:2},{id:3}]),[2])
 assert.deepEqual(safeSelection([],[{id:1}]),[])
 assert.deepEqual(safeSelection([3],[{id:1,children:[{id:3}]}]),[3])
})
test('password validation rejects absent old password, short and mismatched replacements',()=>{
 assert.ok(passwordError('','123456','123456')); assert.ok(passwordError('old','123','123')); assert.ok(passwordError('old','123456','654321')); assert.equal(passwordError('old','123456','123456'),'')
})

