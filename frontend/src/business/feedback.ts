import {showToast,showSuccessToast,showFailToast,showConfirmDialog,showDialog} from 'vant';
export const ElMessage={success:(message:string)=>showSuccessToast(message),error:(message:string)=>showFailToast(message),warning:(message:string)=>showToast(message),info:(message:string)=>showToast(message)};
export const ElMessageBox={confirm:(message:string,title='确认',options:any={})=>showConfirmDialog({title,message,confirmButtonText:options.confirmButtonText||'确认',cancelButtonText:options.cancelButtonText||'取消'}),alert:(message:string,title='提示')=>showDialog({title,message})};
