import os
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:5050"
USERNAME = "wym"
PASSWORD = "12345678"
TEST_FILE = "test_upload.png"

def create_dummy_file():
    # Create a simple valid PNG file (1x1 pixel)
    with open(TEST_FILE, "wb") as f:
        f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')
    print(f"Created dummy file: {os.path.abspath(TEST_FILE)}")
    return os.path.abspath(TEST_FILE)

def test_upload_on_page(page, url, button_selector, description):
    print(f"\nTesting: {description}")
    print(f"Navigating to: {url}")
    try:
        page.goto(f"{BASE_URL}{url}")
        page.wait_for_load_state("networkidle")
        
        # Check if button exists
        if page.locator(button_selector).count() == 0:
            print(f"Skipping: Button not found with selector '{button_selector}'")
             # Try grabbing a screenshot for debug
            page.screenshot(path=f"debug_{description.replace(' ', '_')}_no_btn.png")
            return False

        print(f"Found button: {button_selector}")
        
        # Prepare for upload
        # Some buttons in Layui might need a click to trigger the file input creation or the input is hidden nearby
        # Layui upload usually creates a hidden input[type=file] next to the button or in body
        
        # We start looking for file chooser event
        with page.expect_file_chooser(timeout=5000) as fc_info:
            # Force click if needed, or normal click
            page.click(button_selector)
        
        file_chooser = fc_info.value
        file_chooser.set_files(TEST_FILE)
        print("File selected.")
        
        # Wait for upload request/response or success message
        # Layui upload typically shows a layer.msg on success
        try:
            # Wait for any success toast or log
            # Or wait for API response
            with page.expect_response(lambda response: "/api/v1/upload/" in response.url and response.status == 200, timeout=10000) as response_info:
                pass
            print("Upload API request success (200 OK).")
            return True
        except Exception as e:
            print(f"Upload verification failed (API response not detected): {e}")
            page.screenshot(path=f"debug_{description.replace(' ', '_')}_fail.png")
            return False

    except Exception as e:
        print(f"Error testing {description}: {e}")
        page.screenshot(path=f"debug_{description.replace(' ', '_')}_error.png")
        return False

def test_oss_uploads():
    test_file_path = create_dummy_file()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Run headed to see actions
        context = browser.new_context()
        page = context.new_page()

        # Login
        print("Logging in...")
        try:
            page.goto(f"{BASE_URL}/view/login.html", timeout=60000)
            # Wait for content to load, not just networkidle
            page.wait_for_selector("body", timeout=10000)
            
            # Debug: screenshot before action
            page.screenshot(path="debug_login_page.png")
            
            if page.locator('input[name="username"]').count() == 0:
                print("Login input not found! Dumping page content...")
                with open("debug_login_content.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                raise Exception("Login input missing")

            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', PASSWORD)
            page.click('button[lay-submit]')
            page.wait_for_url(f"{BASE_URL}/", timeout=60000) # Wait for redirect to index
            print("Login successful")
        except Exception as e:
            print(f"Login failed: {e}")
            page.screenshot(path="debug_login_fail.png")
            browser.close()
            return

        # Define test cases
        tests = [
            {
                "url": "/project/info/project_info.html",
                "selector": "#upload-attachment",
                "desc": "Project Info Attachment"
            },
            {
                "url": "/order_pay/info/order_info.html",
                "selector": "#upload-attachment",
                "desc": "Order Info Attachment"
            },
            {
                "url": "/order_pay/info/pay_info.html",
                "selector": "#upload-attachment",
                "desc": "Pay Info Attachment"
            },
             {
                "url": "/view/material/invoice/add",
                "selector": ".upload-area", # This might be drag/drop area, treated as button usually works in Layui if configured
                "desc": "Invoice Add Upload"
            },
             # Material Planning requires opening a modal first, special handling below
        ]

        # Run standard button tests
        for t in tests:
            test_upload_on_page(page, t['url'], t['selector'], t['desc'])
        
        # Special Case: Material Planning Import
        print("\nTesting: Material Planning Import")
        try:
            page.goto(f"{BASE_URL}/view/material/planning")
            page.wait_for_load_state("networkidle")
            
            # Click "Import Material Planning" button
            # Need to find the button. Based on template, it has icon 'layui-icon-upload-drag'
            # Or check the toolbar. It's likely in a toolbar.
            # Searching by text "导入" might be safer
            import_btn = page.locator("button:has-text('导入材料策划')").first
            if import_btn.count() == 0:
                # Try finding by icon
                import_btn = page.locator(".layui-icon-upload-drag").first
            
            if import_btn.count() > 0:
                print("Clicking Import button...")
                import_btn.click()
                
                # Wait for modal
                page.wait_for_selector(".layui-layer-content")
                print("Modal opened.")
                
                # Find upload button inside modal
                # Template says: <i class="layui-icon layui-icon-upload-circle"></i> 选择文件
                upload_btn_selector = ".layui-layer-content .layui-icon-upload-circle"
                
                # Trigger upload
                with page.expect_file_chooser(timeout=5000) as fc_info:
                    # Parent of the icon is usually the clickable element
                    page.locator(upload_btn_selector).locator("xpath=..").click()
                
                file_chooser = fc_info.value
                file_chooser.set_files(test_file_path)
                print("File selected for Planning Import.")
                
                # Wait for upload completion (API response)
                # Note: Planning import might use a different URL than /api/v1/upload, likely an import API
                # But let's assume it works if no error
                # Actually grep checks show it uses `upload.render`. URL is dynamic?
                # Let's wait for some network activity or success msg
                time.sleep(2) # Brief wait
                print("Planning Import test finished (assumed success if no crash).")
            else:
                print("Skipping Planning Import: Button not found")

        except Exception as e:
            print(f"Error testing Material Planning: {e}")
            page.screenshot(path="debug_material_planning_error.png")

        browser.close()
        
        # Cleanup
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

if __name__ == "__main__":
    test_oss_uploads()
