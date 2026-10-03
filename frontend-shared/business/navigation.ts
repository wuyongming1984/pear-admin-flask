/** The mobile workbench is a separate application on the same origin. */
export function mobileWorkbenchHref(menu:{title:string;href?:string|null}){
 const href=menu.href?.trim()||'';
 return href==='/m/'||href==='/m'||(!href&&menu.title.trim()==='移动端工作台')?'/m/':undefined;
}
