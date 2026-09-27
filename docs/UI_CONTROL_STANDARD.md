# 电脑端控件标准

以订单页面为视觉基准：深绿导航、浅色面板、蓝色主操作。

- 普通按钮、单行输入、下拉框：40px 高，8px 圆角，14px 字号。
- 表格紧凑操作：30px 高，13px 字号。
- 主操作 #1e9fff；次操作白底；删除浅红；警告浅黄；禁用灰色。
- 公共变量：static/admin/css/ui-tokens.css。
- 旧版控件适配：static/admin/css/ui-controls.css，经 shared/presentation.html 加载。
- Vue Element Plus 适配：frontend-desktop/src/polish.css，同源变量，独立构建。
- 不对导航菜单、打印纸张或手机布局强行套用桌面控件尺寸。

验证：浏览器实际计算样式确认材料工具栏、发票搜索/下拉/新增、导入弹窗、新版项目筛选均为40px；新版构建通过；侧栏状态与分组展开回归通过。本次未执行新增、删除或真实文件上传。
