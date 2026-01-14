#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据导入工具 - 支持所有数据类型
一键导入供应商、订单、付款单、项目等所有数据
"""

import sys
import os
from pathlib import Path
import traceback

# 确保能找到当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 尝试导入模块，并打印详细错误
import_suppliers = None
try:
    from import_suppliers_mysql import import_suppliers
except ImportError as e:
    print(f"⚠️  无法加载供应商导入模块: {e}")
except Exception as e:
    print(f"⚠️  加载模块时发生未知错误: {e}")


def show_menu():
    """显示菜单"""
    print("\n" + "="*60)
    print("阿里云数据库 - 统一数据导入工具")
    print("="*60)
    print("\n可用的导入选项：\n")
    
    # 根据模块加载情况显示状态
    status_supp = "" if import_suppliers else " [不可用]"
    print(f"  1. 导入供应商数据{status_supp}")
    
    print("  2. 导入订单数据 [开发中]")
    print("  3. 导入付款单数据 [开发中]")
    print("\n  A. 导入所有数据")
    print("  Q. 退出")
    print("\n" + "="*60)


def import_all(mysql_password=None):
    """一键导入所有数据"""
    print("\n开始一键导入...")
    
    if import_suppliers:
        import_suppliers(mysql_password)
    else:
        print("✗ 供应商导入模块不可用")


def main():
    mysql_password = None
    if len(sys.argv) > 1:
        mysql_password = sys.argv[1]
    
    while True:
        show_menu()
        choice = input("\n请选择操作 [1/A/Q]: ").strip().upper()
        
        if choice == 'Q':
            break
        
        if not mysql_password:
            mysql_password = input("请输入MySQL密码: ").strip()
        
        if choice == '1':
            if import_suppliers:
                import_suppliers(mysql_password)
            else:
                print("❌ 错误: 供应商模块未加载，请检查依赖库(pymysql)是否安装")
        elif choice == 'A':
            import_all(mysql_password)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作取消")
