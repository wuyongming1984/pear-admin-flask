import {describe,it,expect} from 'vitest'
import * as XLSX from 'xlsx'
import {readNurseryWorkbook} from './workbook'
function file(rows:any[]):File {const book=XLSX.utils.book_new();XLSX.utils.book_append_sheet(book,XLSX.utils.json_to_sheet(rows),'导入');const data=XLSX.write(book,{type:'array',bookType:'xlsx'});return {arrayBuffer:async()=>data} as File}
describe('nursery workbook preview',()=>{
 it('maps legacy Chinese spreadsheet headings and retains fractional quantities',async()=>{const rows=await readNurseryWorkbook(file([{'苗木名称':'红枫','大类':'苗木','规格':'H3','数量':'2.25','单价':'9.95','位置':'A区'}]));expect(rows[0]).toMatchObject({name:'红枫',category:'苗木',spec:'H3',quantity:'2.25',price:'9.95',location:'A区',unit:'株',import_status:'待导入'})})
 it('validates all rows before any imports can begin',async()=>{await expect(readNurseryWorkbook(file([{name:'红枫',quantity:2},{name:'红枫',quantity:-1}]))).rejects.toThrow('第 3 行数量')})
 it('rejects empty workbook',async()=>{await expect(readNurseryWorkbook(file([]))).rejects.toThrow('没有数据')})
})
