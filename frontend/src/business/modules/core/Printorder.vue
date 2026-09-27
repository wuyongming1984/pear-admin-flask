<script setup lang="ts">
defineProps<{values:Record<string,any>;qr:string}>()
</script>
<template><div class="print-root">

    <div class="print-container">
        
        

        <div class="header">
            <h1>采购订单审批单</h1>
            <div class="sub-title" id="company-name">项目管理系统标准单据</div>
        </div>

        <div class="meta-info">
            <div>单据编号：<span id="order-number" style="font-weight: bold;">{{ values['order-number'] ?? '—' }}</span></div>
            <div>打印日期：<span id="print-date">{{ values['print-date'] ?? '—' }}</span></div>
        </div>

        
        <table class="order-table">
            <tbody>
                <tr>
                    <th>项目名称</th>
                    <td colspan="3" id="project-name" class="strong">{{ values['project-name'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>材料名称</th>
                    <td id="material-name" class="strong">{{ values['material-name'] ?? '—' }}</td>
                    <th>供应商</th>
                    <td id="supplier-name">{{ values['supplier-name'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>材料明细</th>
                    <td colspan="3" id="material-details" style="height: 80px;">{{ values['material-details'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>订单金额</th>
                    <td id="order-amount" class="strong numeric">{{ values['order-amount'] ?? '—' }}</td>
                    <th>当前余额</th>
                    <td id="order-balance" class="numeric">{{ values['order-balance'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>下料日期</th>
                    <td id="cutting-time">{{ values['cutting-time'] ?? '—' }}</td>
                    <th>到场日期</th>
                    <td id="arrival-time">{{ values['arrival-time'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>供应商联系人</th>
                    <td id="contact-person">{{ values['contact-person'] ?? '—' }}</td>
                    <th>联系电话</th>
                    <td id="contact-phone" class="numeric">{{ values['contact-phone'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>材料负责人</th>
                    <td id="material-manager">{{ values['material-manager'] ?? '—' }}</td>
                    <th>分项目负责人</th>
                    <td id="sub-project-manager">{{ values['sub-project-manager'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>付款记录</th>
                    <td colspan="3" id="payment-history" style="font-size: 10pt; color: #555;">{{ values['payment-history'] ?? '—' }}</td>
                </tr>
                <tr>
                    <th>附件文件</th>
                    <td colspan="3" id="attachment-list" style="font-size: 10pt; font-style: italic;">{{ values['attachment-list'] ?? '—' }}</td>
                </tr>
            </tbody>
        </table>

        
        <div class="approval-section">
            <div class="signature-box">
                <div class="signature-title">材料员 / 经办人</div>
                <div class="signature-line"></div>
                <div class="date-line">
                    日期：&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                </div>
            </div>
            <div class="signature-box">
                <div class="signature-title">项目经理审批</div>
                <div class="signature-line"></div>
                <div class="date-line">
                    日期：&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                </div>
            </div>
            <div class="signature-box">
                <div class="signature-title">财务审核</div>
                <div class="signature-line"></div>
                <div class="date-line">
                    日期：&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                </div>
            </div>
            <div class="signature-box">
                <div class="signature-title">公司领导审批</div>
                <div class="signature-line"></div>
                <div class="date-line">
                    日期：&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;/&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                </div>
            </div>
        </div>

        <div style="margin-top: 40px; text-align: center;">
            <img :src="qr" alt="单据二维码" />
            <div style="font-size: 8pt; margin-top: 5px; color: #999;">扫码查看电子版详情</div>
        </div>
    </div>

    </div></template><style scoped>
        .print-root {
            --primary-color: #1a1a1a;
            --accent-color: #555;
            --border-color: #000;
            --table-border: 1px solid #000;
            --font-serif: 'Noto Serif SC', 'SimSun', serif;
            --font-mono: 'JetBrains Mono', 'Courier New', monospace;
        }

        * {
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        .print-root {
            font-family: var(--font-serif);
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: var(--primary-color);
            display: flex;
            justify-content: center;
            min-height: 100vh;
        }

        /* 打印容器 - A4 尺寸视觉模拟 */
        .print-container {
            width: 210mm;
            min-height: 297mm;
            padding: 20mm;
            margin: 20mm auto;
            background: white;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            position: relative;
        }

        /* 标题头 */
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 15px;
        }

        .header h1 {
            font-size: 24pt;
            font-weight: 700;
            margin: 0;
            letter-spacing: 5px;
        }

        .header .sub-title {
            font-size: 12pt;
            margin-top: 10px;
            color: var(--accent-color);
        }

        .meta-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            font-family: var(--font-mono);
            font-size: 10pt;
        }

        /* 表格样式 */
        .order-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 5px;
        }

        .order-table th,
        .order-table td {
            border: var(--table-border);
            padding: 8px 12px;
            text-align: left;
            font-size: 11pt;
            vertical-align: top;
        }

        .order-table th {
            background-color: #f0f0f0;
            font-weight: bold;
            width: 120px;
            text-align: right;
            border-bottom-width: 2px;
            /* 强调表头分割 */
        }

        .order-table td.strong {
            font-weight: bold;
            font-size: 12pt;
        }

        .order-table td.numeric {
            font-family: var(--font-mono);
        }

        /* 布局控制 */
        .row-group {
            display: table-row-group;
        }

        .full-width {
            width: 100%;
        }

        /* 审批签字栏 */
        .approval-section {
            margin-top: 40px;
            display: flex;
            justify-content: space-between;
            padding-top: 20px;
            border-top: 1px dashed #ccc;
        }

        .signature-box {
            width: 23%;
            text-align: center;
        }

        .signature-title {
            font-size: 11pt;
            font-weight: bold;
            margin-bottom: 40px;
            color: #333;
        }

        .signature-line {
            border-bottom: 1px solid #000;
            height: 30px;
            margin: 0 10px;
        }

        .date-line {
            margin-top: 5px;
            font-size: 9pt;
            color: #666;
        }

        /* 打印控制 */
        @media print {
            .print-root {
                background: none;
                display: block;
                height: auto;
            }

            .print-container {
                width: 100%;
                height: auto;
                margin: 0;
                padding: 0;
                box-shadow: none;
            }

            .no-print {
                display: none !important;
            }
        }
    </style>

