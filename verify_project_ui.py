from playwright.sync_api import sync_playwright
import time

def run():
    # User provided URL and Credentials
    BASE_URL = "http://172.18.0.1:5050"
    USERNAME = "wym"
    PASSWORD = "12345678"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print(f"Navigating to login page: {BASE_URL}/login")
        try:
            page.goto(f"{BASE_URL}/login")
        except Exception as e:
            print(f"Initial navigation failed: {e}")
            # Try root URL which might redirect
            page.goto(f"{BASE_URL}/")
        
        # Check if login needed
        if "login" in page.url or page.locator('input[name="username"]').is_visible():
            print("Logging in...")
            page.fill('input[name="username"]', USERNAME)
            page.fill('input[name="password"]', PASSWORD)
            page.click('.login') # Class from login.html
            
            # Wait for navigation or dashboard element
            try:
                page.wait_for_url(f"{BASE_URL}/", timeout=10000)
            except:
                print("URL did not change to root immediately, checking for content...")
            
            print("Login submitted.")
        else:
            print("Already logged in or different page state.")
        
        # Wait for dashboard to load
        print("Waiting for dashboard...")
        page.wait_for_load_state('networkidle')
        
        # Click on Project Management menu
        print("Looking for Project Management menu...")
        
        try:
            # Expand '项目管理' if needed
            # Note: Selectors depend on sidebar structure. 
            # Assuming standard sidebar layout based on previous file reads.
            
            # Look for menu item text
            project_menu = page.locator('span:has-text("项目管理")').first
            if not project_menu.is_visible():
                 project_menu = page.locator('cite:has-text("项目管理")').first
            
            if project_menu.is_visible():
                 print("Found '项目管理', checking if needs expansion...")
                 # Often parent menus are <a> tags wrapping the text
                 parent_link = project_menu.locator('xpath=..')
                 parent_link.click()
                 time.sleep(1) # Animation
            
            print("Clicking Project Info menu...")
            # Submenu item "项目信息"
            info_menu = page.locator('span:has-text("项目信息")').first
            if not info_menu.is_visible():
                info_menu = page.locator('cite:has-text("项目信息")').first
            
            if info_menu.is_visible():
                # Click the link containing the text
                info_menu.locator('xpath=..').click()
            else:
                print("Could not find '项目信息' menu item.")
            
            # Wait for content to load (Ajax fragment load)
            time.sleep(3) 
            
            print("Capturing screenshot of dashboard with Project Info...")
            page.screenshot(path="project_info_dashboard.png")
            
            # Verify #project-page-root existence
            # Since confirmed it's a fragment loaded into main content, search global DOM
            if page.locator('#project-page-root').is_visible():
                print("SUCCESS: Found #project-page-root. Page loaded correctly.")
                
                # Check for Cyber Theme elements
                # e.g., table background, buttons
                styles = page.locator('#project-page-root').evaluate("element => window.getComputedStyle(element).color")
                print(f"Computed style check: {styles}")
                
            else:
                print("ERROR: Did not find #project-page-root.")
                
        except Exception as e:
            print(f"Error interacting with menu: {e}")
            page.screenshot(path="error_state.png")

        browser.close()

if __name__ == "__main__":
    run()
