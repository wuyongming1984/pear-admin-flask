
import os
import sys

files = [
    r'd:\pear_admin\pear-admin-flask\templates\order_pay\order_base.html',
    r'd:\pear_admin\pear-admin-flask\templates\order_pay\pay_base.html'
]
header_template = """<!doctype html>
<html lang="zh-cn">
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <meta name="renderer" content="webkit" />
  <meta http-equiv="X-UA-Compatible" content="IE=edge,chrome=1" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1" />
  <link rel="stylesheet" href="/static/component/layui/css/layui.css" />
  <link rel="stylesheet" href="/static/component/pear/css/pear.css" />
  <link rel="stylesheet" href="/static/admin/css/order_pay_refined.css" />
  <style>
    /* 解决 Pear Admin Tab 覆盖问题 */
    body {{ background: transparent !important; }}
    .refined-container {{ margin: 0 !important; height: 100vh !important; border-radius: 0 !important; }}
  </style>
</head>
<body>
"""

for path in files:
    try:
        if not os.path.exists(path):
            print(f"File not found: {path}")
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"Read {path}, length: {len(content)}")
        
        target = '<div class="refined-container">'
        if target in content:
            idx = content.find(target)
            body = content[idx:]
            title = "订单管理" if "order_base" in path else "付款单管理"
            new_content = header_template.format(title=title) + body
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"SUCCESS: Wrote to {path}, new length: {len(new_content)}")
        else:
            print(f"Target '{target}' not found in {path}")
            # print snippet
            print(f"Snippet: {content[800:1000]}")
            
    except Exception as e:
        print(f"Error processing {path}: {e}")
