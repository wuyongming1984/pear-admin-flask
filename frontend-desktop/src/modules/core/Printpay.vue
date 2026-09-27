<script setup lang="ts">
defineProps<{values:Record<string,any>;qr:string}>()
</script>
<template><div class="print-root">
    
    

    
    <div class="print-canvas">

        
        <div class="header">
            <div class="logo-area">
                <h1>付款审批单</h1>
                <div class="subtitle">PAYMENT APPROVAL SHEET</div>
            </div>
            <div class="meta-area">
                <span class="pay-no" id="pay-number">{{ values['pay-number'] ?? '—' }}</span>
                <div>DATE: <span id="create-date">{{ values['create-date'] ?? '—' }}</span></div>
            </div>
        </div>

        
        <div class="info-grid">

            
            <div class="panel">
                <div class="panel-header">
                    <span>资金往来信息</span>
                    <span>PAYMENT DETAILS</span>
                </div>

                <div class="data-row" style="background: #fdfdfd;">
                    <div class="label" style="font-weight: 700;">付款总额</div>
                    <div class="value">
                        <span class="amount-highlight">¥ <span id="amount-small">{{ values['amount-small'] ?? '—' }}</span></span>
                        <span class="amount-cap" id="amount-big">{{ values['amount-big'] ?? '—' }}</span>
                    </div>
                </div>

                <div class="data-row">
                    <div class="label">收款单位</div>
                    <div class="value" style="font-weight: 600;" id="payee-name">{{ values['payee-name'] ?? '—' }}</div>
                </div>

                <div class="data-row">
                    <div class="label">银行账号</div>
                    <div class="value">
                        <div style="display:flex; flex-direction:column; width: 100%;">
                            <span id="bank-account" style="font-weight:500;">{{ values['bank-account'] ?? '—' }}</span>
                            <span id="bank-name" style="font-size:8pt; color:#666; margin-top:2px;">{{ values['bank-name'] ?? '—' }}</span>
                        </div>
                    </div>
                </div>

                <div class="data-row">
                    <div class="label">付款单位</div>
                    <div class="value" id="payer-name">{{ values['payer-name'] ?? '—' }}</div>
                </div>

                <div class="data-row" style="flex:1; overflow: visible;">
                    <div class="label">款项用途</div>
                    <div class="value"
                        style="align-items: flex-start; line-height: 1.2; padding: 4px 8px; min-height: 80pt; overflow: visible;"
                        id="payment-purpose-container">
                        <div id="payment-purpose"
                            style="width: 100%; word-break: break-all; white-space: pre-wrap; display: block;">{{ values['payment-purpose'] ?? '—' }}</div>
                    </div>
                </div>
            </div>

            
            <div class="panel order-panel">
                <div class="panel-header">
                    <span>关联项目概要</span>
                    <span style="font-size:7pt; color:#666;">PROJECT REF</span>
                </div>

                <div class="data-row">
                    <div class="label">项目名称</div>
                    <div class="value" style="font-weight:600;" id="project-name">{{ values['project-name'] ?? '—' }}</div>
                </div>

                <div class="data-row">
                    <div class="label">订单编号</div>
                    <div class="value" id="order-number">{{ values['order-number'] ?? '—' }}</div>
                </div>

                <div class="data-row">
                    <div class="label">供应商联系人</div>
                    <div class="value" id="contact-person">{{ values['contact-person'] || '—' }}</div>
                </div>

                <div class="data-row">
                    <div class="label">材料服务</div>
                    <div class="value" id="material-name">{{ values['material-name'] ?? '—' }}</div>
                </div>

                <div class="data-row">
                    <div class="label">订单总额</div>
                    <div class="value">¥ <span id="order-amount">{{ values['order-amount'] ?? '—' }}</span></div>
                </div>

                <div class="data-row">
                    <div class="label">累计已付</div>
                    <div class="value">
                        <span style="font-weight:500;">¥ <span id="paid-total">{{ values['paid-total'] ?? '—' }}</span></span>
                        <span style="font-size:7pt; color:#888; margin-left:4px;">(含本次)</span>
                    </div>
                </div>

                <div class="data-row" style="flex:1; border-bottom:none;">
                    <div class="label">付款进度</div>
                    <div class="value">
                        <div style="width:100%;">
                            <div style="font-weight:700; font-size:12pt;" id="pay-ratio">{{ values['pay-ratio'] ?? '—' }}</div>
                            <div style="font-size:7pt; color:#888;">剩余未付: ¥<span id="order-balance">{{ values['order-balance'] ?? '—' }}</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        
        <div class="panel" style="border:none;">
            
            <div class="approval-grid">
                <div class="approve-box">
                    <div class="approve-title">经办人 / Handler</div>
                    <div class="approve-sign-area" id="handler-sign">{{ values['handler-sign'] ?? '—' }}</div>
                    <div class="approve-date">Date: . . . . / . . / . .</div>
                </div>
                <div class="approve-box">
                    <div class="approve-title">项目负责人 / PM</div>
                    <div class="approve-sign-area"></div>
                    <div class="approve-date">Date: . . . . / . . / . .</div>
                </div>
                <div class="approve-box">
                    <div class="approve-title">副总经理审 / puty General Manager</div>
                    <div class="approve-sign-area"></div>
                    <div class="approve-date">Date: . . . . / . . / . .</div>
                </div>
                <div class="approve-box">
                    <div class="approve-title">总经理审批 / General Manager</div>
                    <div class="approve-sign-area"></div>
                    <div class="approve-date">Date: . . . . / . . / . .</div>
                </div>
            </div>
        </div>

        
        <div class="footer">
            <div class="uuid">
                <div>UNIQUE ID VERIFICATION</div>
                <div style="letter-spacing:1px; margin-top:2px;" id="uuid-text">{{ values['uuid-text'] ?? '—' }}</div>
            </div>
            <img :src="qr" alt="单据二维码" />
        </div>

    </div>

    
    </div></template><style scoped>
        .print-root {
            --font-ui: 'Inter', -apple-system, sans-serif;
            --font-data: 'JetBrains Mono', monospace;
            --font-heading: 'Noto Serif SC', serif;
            --color-black: #000;
            --color-gray: #444;
            --color-light-gray: #f2f2f2;
            --border-width: 0.5pt;
        }

        

        * {
            box-sizing: border-box;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }

        .print-root {
            font-family: var(--font-ui);
            font-size: 9pt;
            color: var(--color-black);
            margin: 0;
            padding: 0;
            background-color: #fff;
            /* White background for print */
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }

        .print-canvas {
            width: 210mm;
            min-height: 148mm;
            /* Fixed height for A5 Landscape */
            padding: 7mm 10mm;
            /* Reduced padding */
            background: white;
            position: relative;
            /* Flex layout for vertical distribution */
            display: flex;
            flex-direction: column;
            gap: 8px;
            /* Tighter gap */
        }

        /* Screen-only Container Styling */
        @media screen {
            .print-root {
                background-color: #525659;
                /* Browser reader gray */
            }

            .print-canvas {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
                margin: 20px;
            }

            .no-print {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 999;
            }

            .print-btn {
                background: #000;
                color: #fff;
                border: none;
                padding: 10px 20px;
                font-family: var(--font-ui);
                font-weight: 500;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-radius: 4px;
            }

            .print-btn:hover {
                background: #333;
            }
        }

        @media print {
            .no-print {
                display: none !important;
            }

            .print-root {
                margin: 0;
                background-color: white;
            }

            .print-canvas {
                margin: 0;
                box-shadow: none;
                page-break-after: avoid;
                /* Prevent simple page break */
            }
        }

        /* Header Section - Modern & Compact */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            padding-bottom: 6px;
            border-bottom: 2pt solid var(--color-black);
            margin-bottom: 2px;
        }

        .logo-area h1 {
            font-family: var(--font-heading);
            font-size: 18pt;
            /* Reduced from 26pt */
            margin: 0;
            line-height: 1;
            letter-spacing: 0.5px;
        }

        .logo-area .subtitle {
            font-size: 8pt;
            color: var(--color-gray);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-top: 4px;
        }

        .meta-area {
            text-align: right;
            font-family: var(--font-data);
            font-size: 8pt;
            color: var(--color-gray);
        }

        .meta-area .pay-no {
            font-weight: 700;
            color: var(--color-black);
            font-size: 10pt;
            display: block;
            margin-bottom: 2px;
        }

        /* Swiss Grid Layout */
        .info-grid {
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            /* Left (Pay Info) wider than Right (Order Info) */
            gap: 10px;
            flex: 1;
            /* Take remaining space */
        }

        .panel { padding:0; margin:0; border-radius:0;
            border: var(--border-width) solid var(--color-black);
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            font-family: var(--font-ui);
            font-size: 8pt;
            font-weight: 700;
            text-transform: uppercase;
            background-color: var(--color-light-gray);
            padding: 4px 8px;
            border-bottom: var(--border-width) solid var(--color-black);
            display: flex;
            justify-content: space-between;
        }

        /* Data Rows */
        .data-row {
            display: flex;
            border-bottom: var(--border-width) solid #ddd;
        }

        .data-row:last-child {
            border-bottom: none;
        }

        .label {
            width: 70px;
            /* Fixed label width */
            padding: 4px 6px;
            font-size: 8pt;
            color: var(--color-gray);
            border-right: var(--border-width) solid #ddd;
            display: flex;
            align-items: center;
        }

        .value {
            flex: 1;
            padding: 4px 8px;
            font-family: var(--font-data);
            font-size: 9pt;
            display: flex;
            align-items: center;
        }

        /* Amount Emphasis */
        .amount-highlight {
            font-size: 14pt;
            font-weight: 700;
        }

        .amount-cap {
            font-size: 9pt;
            font-family: var(--font-heading);
            margin-left: 8px;
            color: var(--color-gray);
        }

        /* Order Panel specific adjustments */
        .order-panel .label {
            width: 84px;
            flex-shrink: 0;
        }

        .order-panel .value {
            min-width: 0;
            overflow-wrap: anywhere;
        }

        /* Approval Grid - Compact */
        .approval-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            border: var(--border-width) solid var(--color-black);
            height: 35mm;
            /* Fixed efficient height ~130px */
        }

        .approve-box {
            border-right: var(--border-width) solid var(--color-black);
            display: flex;
            flex-direction: column;
            position: relative;
        }

        .approve-box:last-child {
            border-right: none;
        }

        .approve-title {
            font-size: 8pt;
            font-weight: 600;
            text-align: center;
            background: var(--color-light-gray);
            padding: 2px 0;
            border-bottom: var(--border-width) solid var(--color-black);
        }

        .approve-sign-area {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Brush Script MT', cursive;
            /* Fallback for signature style */
            font-size: 14pt;
        }

        .approve-date {
            position: absolute;
            bottom: 2px;
            right: 4px;
            font-family: var(--font-data);
            font-size: 7pt;
            color: #888;
        }

        /* Footer */
        .footer {
            display: flex;
            justify-content: flex-end;
            align-items: flex-end;
            margin-top: 0;
            gap: 10px;
        }

        .uuid {
            font-family: var(--font-data);
            font-size: 7pt;
            color: #888;
            max-width: 200px;
            text-align: right;
            line-height: 1.1;
        }

        /* Utility */
        .text-truncate {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    </style>



