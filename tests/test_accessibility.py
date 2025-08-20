import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from axe_selenium_python import Axe
import time
import json


class AccessibilityTestCase(unittest.TestCase):
    """
    Accessibility test cases for the Voice Exam System using axe-core
    Tests WCAG 2.1 compliance across all exam interface pages
    """

    @classmethod
    def setUpClass(cls):
        """Set up Chrome driver with accessibility-friendly options"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Remove for visual debugging
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Install and setup ChromeDriver
        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=chrome_options)
        cls.driver.implicitly_wait(10)
        cls.axe = Axe(cls.driver)
        
        # Base URL for the application
        cls.base_url = "http://localhost:8000"

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        cls.driver.quit()

    def setUp(self):
        """Reset before each test"""
        self.driver.delete_all_cookies()

    def test_exam_interface_accessibility(self):
        """Test main exam interface page for accessibility violations"""
        print("\n🔍 Testing Exam Interface Accessibility...")
        
        # Navigate to exam interface
        self.driver.get(f"{self.base_url}/")
        
        # Wait for page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Inject axe-core and run accessibility scan
        self.axe.inject()
        results = self.axe.run()
        
        # Check for violations
        violations = results.get("violations", [])
        
        if violations:
            print(f"❌ Found {len(violations)} accessibility violations:")
            for violation in violations:
                print(f"  - {violation['help']}")
                print(f"    Impact: {violation['impact']}")
                print(f"    Tags: {', '.join(violation['tags'])}")
                for node in violation['nodes']:
                    print(f"    Element: {node['html'][:100]}...")
                print()
        else:
            print("✅ No accessibility violations found!")
            
        # Assert no critical or serious violations
        critical_violations = [v for v in violations if v['impact'] in ['critical', 'serious']]
        self.assertEqual(len(critical_violations), 0, 
                        f"Found {len(critical_violations)} critical/serious accessibility violations")

    def test_session_list_accessibility(self):
        """Test session list page accessibility"""
        print("\n🔍 Testing Session List Accessibility...")
        
        self.driver.get(f"{self.base_url}/sessions/")
        
        # Wait for page load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        self.axe.inject()
        results = self.axe.run()
        
        violations = results.get("violations", [])
        critical_violations = [v for v in violations if v['impact'] in ['critical', 'serious']]
        
        if violations:
            print(f"❌ Found {len(violations)} accessibility violations")
            self._print_violations(violations)
        else:
            print("✅ No accessibility violations found!")
            
        self.assertEqual(len(critical_violations), 0)

    def test_keyboard_navigation(self):
        """Test keyboard navigation accessibility"""
        print("\n⌨️ Testing Keyboard Navigation...")
        
        self.driver.get(f"{self.base_url}/")
        
        # Find all interactive elements
        interactive_elements = self.driver.find_elements(
            By.CSS_SELECTOR, 
            "button, input, select, textarea, a[href], [tabindex]:not([tabindex='-1'])"
        )
        
        print(f"Found {len(interactive_elements)} interactive elements")
        
        # Check each element is focusable
        focusable_count = 0
        for element in interactive_elements:
            try:
                element.send_keys("")  # Try to focus
                focusable_count += 1
            except:
                pass
                
        print(f"✅ {focusable_count}/{len(interactive_elements)} elements are keyboard accessible")
        
        # At least 80% of interactive elements should be focusable
        if interactive_elements:
            focus_ratio = focusable_count / len(interactive_elements)
            self.assertGreaterEqual(focus_ratio, 0.8, 
                                   "Less than 80% of interactive elements are keyboard accessible")

    def test_screen_reader_compatibility(self):
        """Test screen reader compatibility features"""
        print("\n🔊 Testing Screen Reader Compatibility...")
        
        self.driver.get(f"{self.base_url}/")
        
        # Check for ARIA labels and roles
        aria_elements = self.driver.find_elements(By.CSS_SELECTOR, "[aria-label], [aria-labelledby], [role]")
        print(f"Found {len(aria_elements)} elements with ARIA attributes")
        
        # Check for alt text on images
        images = self.driver.find_elements(By.TAG_NAME, "img")
        images_with_alt = [img for img in images if img.get_attribute("alt")]
        print(f"Images with alt text: {len(images_with_alt)}/{len(images)}")
        
        # Check for form labels
        inputs = self.driver.find_elements(By.TAG_NAME, "input")
        labeled_inputs = 0
        for input_elem in inputs:
            input_id = input_elem.get_attribute("id")
            if input_id:
                labels = self.driver.find_elements(By.CSS_SELECTOR, f"label[for='{input_id}']")
                if labels or input_elem.get_attribute("aria-label"):
                    labeled_inputs += 1
                    
        print(f"Labeled inputs: {labeled_inputs}/{len(inputs)}")
        
        # Assertions
        if images:
            alt_ratio = len(images_with_alt) / len(images)
            self.assertGreaterEqual(alt_ratio, 0.9, "Less than 90% of images have alt text")

    def test_color_contrast_and_visual_accessibility(self):
        """Test color contrast and visual accessibility"""
        print("\n🎨 Testing Color Contrast...")
        
        self.driver.get(f"{self.base_url}/")
        
        # Run axe with specific color contrast rules
        self.axe.inject()
        results = self.axe.run(options={
            "runOnly": {
                "type": "tag",
                "values": ["wcag2aa", "wcag21aa"]
            }
        })
        
        color_violations = [v for v in results.get("violations", []) 
                           if "color-contrast" in v.get("id", "")]
        
        if color_violations:
            print(f"❌ Found {len(color_violations)} color contrast violations")
            self._print_violations(color_violations)
        else:
            print("✅ No color contrast violations found!")
            
        self.assertEqual(len(color_violations), 0, "Color contrast violations detected")

    def test_form_accessibility(self):
        """Test form accessibility specifically"""
        print("\n📝 Testing Form Accessibility...")
        
        self.driver.get(f"{self.base_url}/")
        
        # Check for form-related accessibility issues
        self.axe.inject()
        results = self.axe.run(options={
            "runOnly": {
                "type": "tag", 
                "values": ["wcag2a", "wcag2aa", "section508"]
            }
        })
        
        form_violations = [v for v in results.get("violations", [])
                          if any(tag in ["form", "input"] for tag in v.get("tags", []))]
        
        if form_violations:
            print(f"❌ Found {len(form_violations)} form accessibility violations")
            self._print_violations(form_violations)
        else:
            print("✅ No form accessibility violations found!")
            
        self.assertEqual(len(form_violations), 0)

    def test_mobile_accessibility(self):
        """Test mobile accessibility by changing viewport"""
        print("\n📱 Testing Mobile Accessibility...")
        
        # Set mobile viewport
        self.driver.set_window_size(375, 667)  # iPhone SE dimensions
        self.driver.get(f"{self.base_url}/")
        
        # Wait for responsive layout to load
        time.sleep(2)
        
        self.axe.inject()
        results = self.axe.run()
        
        violations = results.get("violations", [])
        mobile_critical = [v for v in violations if v['impact'] in ['critical', 'serious']]
        
        if violations:
            print(f"❌ Found {len(violations)} mobile accessibility violations")
            self._print_violations(violations)
        else:
            print("✅ No mobile accessibility violations found!")
            
        # Reset window size
        self.driver.set_window_size(1920, 1080)
        
        self.assertEqual(len(mobile_critical), 0, "Critical mobile accessibility issues found")

    def _print_violations(self, violations):
        """Helper method to print violation details"""
        for violation in violations:
            print(f"  - {violation['help']}")
            print(f"    Impact: {violation['impact']}")
            print(f"    Description: {violation['description']}")
            print(f"    Help URL: {violation.get('helpUrl', 'N/A')}")
            for node in violation['nodes'][:2]:  # Show first 2 nodes
                print(f"    Element: {node['html'][:100]}...")
            print()

    def generate_accessibility_report(self):
        """Generate a comprehensive accessibility report"""
        print("\n📊 Generating Accessibility Report...")
        
        self.driver.get(f"{self.base_url}/")
        self.axe.inject()
        results = self.axe.run()
        
        # Save full report to file
        report_file = "accessibility_report.json"
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"✅ Full accessibility report saved to {report_file}")
        
        # Print summary
        violations = results.get("violations", [])
        passes = results.get("passes", [])
        
        print(f"\n📈 Accessibility Summary:")
        print(f"  ✅ Passed: {len(passes)} rules")
        print(f"  ❌ Violations: {len(violations)} rules")
        
        if violations:
            by_impact = {}
            for v in violations:
                impact = v['impact']
                by_impact[impact] = by_impact.get(impact, 0) + 1
            
            for impact, count in by_impact.items():
                print(f"    {impact.upper()}: {count}")


        def test_generate_full_report(self):
            """Always generate a full accessibility report"""
            self.generate_accessibility_report()
            
if __name__ == "__main__":
    # Run all accessibility tests
    unittest.main(verbosity=2)
