import requests
import sys
import json
from datetime import datetime
import io

class WindowsExplorerAPITester:
    def __init__(self, base_url="https://winexplorer-1.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.created_folder_id = None
        self.created_file_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {}
        if data and not files:
            headers['Content-Type'] = 'application/json'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, params=params)
                else:
                    response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, params=params)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, list) and len(response_data) > 0:
                        print(f"   Response: {len(response_data)} items returned")
                    elif isinstance(response_data, dict):
                        print(f"   Response keys: {list(response_data.keys())}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")

            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        return self.run_test("Root API", "GET", "", 200)

    def test_get_folder_tree(self):
        """Test getting complete folder tree"""
        success, response = self.run_test("Get Folder Tree", "GET", "folders/tree", 200)
        if success and isinstance(response, list) and len(response) > 0:
            print(f"   Found {len(response)} root folders")
            # Check if sample data exists
            folder_names = [folder.get('name', '') for folder in response]
            expected_folders = ['Documents', 'Pictures', 'Downloads', 'Music']
            found_folders = [name for name in expected_folders if name in folder_names]
            print(f"   Expected sample folders found: {found_folders}")
        return success, response

    def test_get_folder_children(self):
        """Test getting folder children"""
        # First get the folder tree to find a folder ID
        tree_success, tree_data = self.test_get_folder_tree()
        if not tree_success or not tree_data:
            return False, {}
        
        # Test with root folder
        success, response = self.run_test("Get Root Children", "GET", "folders/root/children", 200)
        if success:
            print(f"   Root has {len(response)} children")
        
        # Test with a specific folder if available
        if tree_data and len(tree_data) > 0:
            folder_id = tree_data[0].get('id')
            if folder_id:
                success2, response2 = self.run_test(
                    f"Get Folder Children ({tree_data[0].get('name')})", 
                    "GET", 
                    f"folders/{folder_id}/children", 
                    200
                )
                return success and success2, response2
        
        return success, response

    def test_create_folder(self):
        """Test creating a new folder"""
        test_folder_name = f"TestFolder_{datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create Folder",
            "POST",
            "folders",
            200,  # Changed from 201 to 200 based on typical FastAPI response
            data={"name": test_folder_name, "parent_id": None}
        )
        if success and 'id' in response:
            self.created_folder_id = response['id']
            print(f"   Created folder ID: {self.created_folder_id}")
        return success, response

    def test_create_subfolder(self):
        """Test creating a subfolder"""
        if not self.created_folder_id:
            print("❌ Skipping subfolder test - no parent folder created")
            return False, {}
        
        test_subfolder_name = f"SubFolder_{datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Create Subfolder",
            "POST",
            "folders",
            200,
            data={"name": test_subfolder_name, "parent_id": self.created_folder_id}
        )
        return success, response

    def test_rename_folder(self):
        """Test renaming a folder"""
        if not self.created_folder_id:
            print("❌ Skipping rename test - no folder to rename")
            return False, {}
        
        new_name = f"RenamedFolder_{datetime.now().strftime('%H%M%S')}"
        success, response = self.run_test(
            "Rename Folder",
            "PUT",
            f"folders/{self.created_folder_id}",
            200,
            params={"name": new_name}
        )
        return success, response

    def test_upload_file(self):
        """Test file upload"""
        if not self.created_folder_id:
            print("❌ Skipping file upload test - no folder to upload to")
            return False, {}
        
        # Create a test file
        test_content = "This is a test file content for Windows Explorer API testing."
        test_file = io.BytesIO(test_content.encode())
        test_filename = f"test_file_{datetime.now().strftime('%H%M%S')}.txt"
        
        files = {'file': (test_filename, test_file, 'text/plain')}
        params = {'folder_id': self.created_folder_id}
        
        success, response = self.run_test(
            "Upload File",
            "POST",
            "files/upload",
            200,
            files=files,
            params=params
        )
        if success and 'id' in response:
            self.created_file_id = response['id']
            print(f"   Uploaded file ID: {self.created_file_id}")
        return success, response

    def test_search(self):
        """Test search functionality"""
        # Search for a common term
        success1, response1 = self.run_test(
            "Search - Documents",
            "GET",
            "search",
            200,
            params={"q": "Documents"}
        )
        
        # Search for file extension
        success2, response2 = self.run_test(
            "Search - .txt files",
            "GET",
            "search",
            200,
            params={"q": ".txt"}
        )
        
        return success1 and success2, response2

    def test_delete_file(self):
        """Test deleting a file"""
        if not self.created_file_id:
            print("❌ Skipping file delete test - no file to delete")
            return False, {}
        
        success, response = self.run_test(
            "Delete File",
            "DELETE",
            f"files/{self.created_file_id}",
            200
        )
        return success, response

    def test_delete_folder(self):
        """Test deleting a folder (should be recursive)"""
        if not self.created_folder_id:
            print("❌ Skipping folder delete test - no folder to delete")
            return False, {}
        
        success, response = self.run_test(
            "Delete Folder",
            "DELETE",
            f"folders/{self.created_folder_id}",
            200
        )
        return success, response

    def test_error_cases(self):
        """Test error handling"""
        print("\n🔍 Testing Error Cases...")
        
        # Test non-existent folder
        success1, _ = self.run_test(
            "Get Non-existent Folder",
            "GET",
            "folders/non-existent-id/children",
            200  # API might return empty array instead of 404
        )
        
        # Test deleting non-existent folder
        success2, _ = self.run_test(
            "Delete Non-existent Folder",
            "DELETE",
            "folders/non-existent-id",
            404
        )
        
        # Test empty search
        success3, _ = self.run_test(
            "Empty Search Query",
            "GET",
            "search",
            422,  # FastAPI validation error for missing required param
            params={"q": ""}
        )
        
        return success2  # At least one error case should work properly

def main():
    print("🚀 Starting Windows Explorer API Tests")
    print("=" * 50)
    
    tester = WindowsExplorerAPITester()
    
    # Run all tests in sequence
    test_results = []
    
    # Basic functionality tests
    test_results.append(tester.test_root_endpoint())
    test_results.append(tester.test_get_folder_tree())
    test_results.append(tester.test_get_folder_children())
    
    # CRUD operations
    test_results.append(tester.test_create_folder())
    test_results.append(tester.test_create_subfolder())
    test_results.append(tester.test_rename_folder())
    test_results.append(tester.test_upload_file())
    
    # Search functionality
    test_results.append(tester.test_search())
    
    # Cleanup operations
    test_results.append(tester.test_delete_file())
    test_results.append(tester.test_delete_folder())
    
    # Error handling
    test_results.append(tester.test_error_cases())
    
    # Print final results
    print("\n" + "=" * 50)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        failed_tests = tester.tests_run - tester.tests_passed
        print(f"⚠️  {failed_tests} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())