import requests # for making HTTP requests
import concurrent.futures # for concurrency or running multiple tasks simultaneously
import time
from datetime import datetime
import csv # for reading CSV files

# Configuration
BASE_URL = "https://county-dashboard.uc.r.appspot.com/"
NUM_CONCURRENT_USERS = 100  # Test with 60 simultaneous users
TIMEOUT = 350  # seconds

def load_county_data(csv_file):
    """
    Load county data from CSV file
    Your CSV has columns: County, State, County Name, Key
    """
    counties = []
    
    # Try multiple encodings (utf-8-sig handles BOM)
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                
                # Clean up column names (remove extra spaces and BOM characters)
                reader.fieldnames = [name.strip().replace('\ufeff', '') for name in reader.fieldnames]
                
                print(f"📋 Found columns: {reader.fieldnames}")
                
                for row in reader:
                    try:
                        # Handle the column names from your file
                        county_code = row['County'].strip()
                        state = row['State'].strip()
                        county_name = row['County Name'].strip()
                        key = row['Key'].strip()
                        
                        counties.append({
                            'code': county_code,
                            'state': state,
                            'name': county_name,
                            'key': key,
                            'url': f"{BASE_URL}?county={county_code}&key={key}"
                        })
                    except KeyError as e:
                        print(f"❌ Error: Missing column: {e}")
                        print(f"   Available columns: {list(row.keys())}")
                        return []
                        
            print(f"✅ Loaded {len(counties)} counties from {csv_file} (encoding: {encoding})")
            return counties
            
        except UnicodeDecodeError:
            continue  # Try next encoding
        except Exception as e:
            print(f"❌ Error with encoding {encoding}: {e}")
            continue
    
    # If all encodings failed
    print(f"❌ Could not read {csv_file} with any standard encoding")
    return []

def test_county_link(county_data, user_id):
    """Test a single county's dashboard link"""
    
    result = {
        'user_id': user_id,
        'county_code': county_data['code'],
        'state': county_data['state'],
        'county_name': county_data['name'],
        'url': county_data['url'],
        'success': False,
        'status_code': None,
        'response_time': None,
        'error': None,
        'data_check': None
    }
    
    try:
        print(f"User {user_id}: Testing {county_data['name']}, {county_data['state']} ({county_data['code']})...")
        
        start_time = time.time()
        response = requests.get(county_data['url'], timeout=TIMEOUT)
        response_time = time.time() - start_time
        
        result['status_code'] = response.status_code
        result['response_time'] = response_time
        
        if response.status_code == 200:
            result['success'] = True
            
            # Verify the response contains the correct county data
            response_text = response.text.lower()
            county_name_lower = county_data['name'].lower()
            
            if county_data['code'] in response_text or county_name_lower in response_text:
                result['data_check'] = 'PASS'
            else:
                result['data_check'] = 'UNCERTAIN'
        else:
            result['error'] = f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        result['error'] = "Request timeout"
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error"
    except Exception as e:
        result['error'] = f"Exception: {str(e)}"
    
    return result

def run_stress_test(counties, num_users):
    """Run stress test with specified number of concurrent users"""
    
    print("\n" + "=" * 70)
    print(f"STARTING STRESS TEST")
    print("=" * 70)
    print(f"Total Counties Available: {len(counties)}")
    print(f"Concurrent Users: {num_users}")
    print(f"Base URL: {BASE_URL}")
    print("-" * 70)
    
    # Select random sample of counties to test
    import random
    test_counties = random.choices(counties, k=num_users)
    
    # Show distribution by state
    state_counts = {}
    for county in test_counties:
        state_counts[county['state']] = state_counts.get(county['state'], 0) + 1
    
    print("\nTesting Sample (by state):")
    for state, count in sorted(state_counts.items())[:10]:
        print(f"  {state}: {count} counties")
    if len(state_counts) > 10:
        print(f"  ... and {len(state_counts) - 10} more states")
    
    print("\nFirst 10 counties being tested:")
    for i, county in enumerate(test_counties[:10], 1):
        print(f"  {i}. {county['name']}, {county['state']} ({county['code']})")
    if num_users > 10:
        print(f"  ... and {num_users - 10} more")
    print("-" * 70)
    
    start_time = datetime.now()
    
    # Run concurrent tests
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [
            executor.submit(test_county_link, county, i) 
            for i, county in enumerate(test_counties, 1)
        ]
        
        # Collect results
        results = []
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            results.append(future.result())
            
            # Progress update every 10 completions
            if completed % 10 == 0 or completed == num_users:
                print(f"Progress: {completed}/{num_users} tests completed")
    
    end_time = datetime.now()
    
    # Analyze results
    print("\n" + "=" * 70)
    print("STRESS TEST RESULTS")
    print("=" * 70)
    
    total_tests = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total_tests - successful
    
    response_times = [r['response_time'] for r in results if r['response_time']]
    status_codes = {}
    errors = {}
    data_checks = {'PASS': 0, 'UNCERTAIN': 0, 'FAIL': 0}
    
    for result in results:
        # Status codes
        if result['status_code']:
            status_codes[result['status_code']] = status_codes.get(result['status_code'], 0) + 1
        
        # Errors
        if result['error']:
            errors[result['error']] = errors.get(result['error'], 0) + 1
        
        # Data validation
        if result['data_check']:
            data_checks[result['data_check']] += 1
    
    # Print statistics
    print(f"\n📊 OVERALL STATISTICS")
    print(f"Total Tests Run: {total_tests}")
    print(f"Successful: {successful} ({successful/total_tests*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
    
    duration = (end_time - start_time).total_seconds()
    print(f"\n⏱️  PERFORMANCE")
    print(f"Test Duration: {duration:.2f} seconds")
    print(f"Requests/Second: {total_tests/duration:.2f}")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"\nResponse Times:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min(response_times):.3f}s")
        print(f"  Max: {max(response_times):.3f}s")
        print(f"  Median: {sorted(response_times)[len(response_times)//2]:.3f}s")
    
    print(f"\n📡 HTTP STATUS CODES")
    for code, count in sorted(status_codes.items()):
        print(f"  {code}: {count} requests ({count/total_tests*100:.1f}%)")
    
    if errors:
        print(f"\n❌ ERRORS ENCOUNTERED")
        for error, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error}: {count} occurrences")
    
    print(f"\n✅ DATA VALIDATION")
    print(f"  Passed: {data_checks['PASS']}")
    print(f"  Uncertain: {data_checks['UNCERTAIN']}")
    print(f"  Failed: {data_checks['FAIL']}")
    
    # Show failed tests details
    failed_tests = [r for r in results if not r['success']]
    if failed_tests:
        print(f"\n⚠️  FAILED TESTS DETAILS (showing first 10):")
        for result in failed_tests[:10]:
            print(f"  {result['county_name']}, {result['state']} ({result['county_code']}): {result['error']}")
    
    # Final verdict
    print("\n" + "=" * 70)
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        print("   System successfully handled all concurrent requests.")
    elif failed < total_tests * 0.05:  # Less than 5% failure
        print("⚠️  MOSTLY SUCCESSFUL with minor issues")
        print(f"   {failed} failures out of {total_tests} tests")
    else:
        print("❌ SIGNIFICANT ISSUES DETECTED")
        print(f"   {failed} failures out of {total_tests} tests")
        print("   Review error details above.")
    print("=" * 70)
    
    # Save detailed results to file
    save_results_to_file(results, start_time)
    
    return results

def save_results_to_file(results, timestamp):
    """Save detailed results to CSV file"""
    filename = f"stress_test_results_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as f:
        fieldnames = ['user_id', 'county_code', 'state', 'county_name', 'success', 
                     'status_code', 'response_time', 'data_check', 'error', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\n💾 Detailed results saved to: {filename}")

# Main execution
if __name__ == "__main__":
    print("=" * 70)
    print("COUNTY DASHBOARD STRESS TEST")
    print("=" * 70)
    
    # Load county data from your file
    counties = load_county_data('County-Key.csv')
    
    if not counties:
        print("❌ No county data loaded. Exiting.")
        exit()
    
    # Run stress test
    print("\n🚀 Starting stress test...")
    results = run_stress_test(counties, NUM_CONCURRENT_USERS)
    print("\n🚀 Stress test completed.")

## Stress test for 500 counties 

import requests # for making HTTP requests
import concurrent.futures # for concurrency or running multiple tasks simultaneously
import time
from datetime import datetime
import csv # for reading CSV files

# Configuration
BASE_URL = "https://county-dashboard.uc.r.appspot.com/"
NUM_CONCURRENT_USERS = 500  # Test with 500 simultaneous users
TIMEOUT = 30  # seconds

def load_county_data(csv_file):
    """
    Load county data from CSV file
    Your CSV has columns: County, State, County Name, Key
    """
    counties = []
    
    # Try multiple encodings (utf-8-sig handles BOM)
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                
                # Clean up column names (remove extra spaces and BOM characters)
                reader.fieldnames = [name.strip().replace('\ufeff', '') for name in reader.fieldnames]
                
                print(f"📋 Found columns: {reader.fieldnames}")
                
                for row in reader:
                    try:
                        # Handle the column names from your file
                        county_code = row['County'].strip()
                        state = row['State'].strip()
                        county_name = row['County Name'].strip()
                        key = row['Key'].strip()
                        
                        counties.append({
                            'code': county_code,
                            'state': state,
                            'name': county_name,
                            'key': key,
                            'url': f"{BASE_URL}?county={county_code}&key={key}"
                        })
                    except KeyError as e:
                        print(f"❌ Error: Missing column: {e}")
                        print(f"   Available columns: {list(row.keys())}")
                        return []
                        
            print(f"✅ Loaded {len(counties)} counties from {csv_file} (encoding: {encoding})")
            return counties
            
        except UnicodeDecodeError:
            continue  # Try next encoding
        except Exception as e:
            print(f"❌ Error with encoding {encoding}: {e}")
            continue
    
    # If all encodings failed
    print(f"❌ Could not read {csv_file} with any standard encoding")
    return []

def test_county_link(county_data, user_id):
    """Test a single county's dashboard link with improved validation"""
    
    result = {
        'user_id': user_id,
        'county_code': county_data['code'],
        'state': county_data['state'],
        'county_name': county_data['name'],
        'url': county_data['url'],
        'success': False,
        'status_code': None,
        'response_time': None,
        'error': None,
        'data_check': None
    }
    
    try:
        print(f"User {user_id}: Testing {county_data['name']}, {county_data['state']} ({county_data['code']})...")
        
        start_time = time.time()
        response = requests.get(county_data['url'], timeout=TIMEOUT)
        response_time = time.time() - start_time
        
        result['status_code'] = response.status_code
        result['response_time'] = response_time
        
        if response.status_code == 200:
            result['success'] = True
            
            # IMPROVED DATA VALIDATION
            # Convert response to lowercase for case-insensitive matching
            response_text = response.text.lower()
            county_name_lower = county_data['name'].lower()
            county_code = county_data['code']
            state_lower = county_data['state'].lower()
            
            # Multiple checks to verify correct county data
            checks_passed = 0
            
            # Check 1: County name in response
            if county_name_lower in response_text:
                checks_passed += 1
            
            # Check 2: County code in response (handles "County: 01001" format)
            if county_code in response_text:
                checks_passed += 1
            
            # Check 3: State name in response
            if state_lower in response_text:
                checks_passed += 1
            
            # Check 4: Look for title format "CountyName, State"
            title_format = f"{county_name_lower}, {state_lower}"
            if title_format in response_text:
                checks_passed += 1
            
            # Check 5: Look for "County: CODE" format specifically
            county_code_format = f"county: {county_code}"
            if county_code_format in response_text:
                checks_passed += 1
            
            # Determine validation result based on checks passed
            if checks_passed >= 3:
                result['data_check'] = 'PASS'  # Strong confidence
            elif checks_passed >= 1:
                result['data_check'] = 'LIKELY_PASS'  # Some confidence
            else:
                result['data_check'] = 'UNCERTAIN'  # Couldn't verify
                
        else:
            result['error'] = f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        result['error'] = "Request timeout"
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error"
    except Exception as e:
        result['error'] = f"Exception: {str(e)}"
    
    return result

def run_stress_test(counties, num_users):
    """Run stress test with specified number of concurrent users"""
    
    print("\n" + "=" * 70)
    print(f"STARTING STRESS TEST")
    print("=" * 70)
    print(f"Total Counties Available: {len(counties)}")
    print(f"Concurrent Users: {num_users}")
    print(f"Base URL: {BASE_URL}")
    print("-" * 70)
    
    # Select random sample of counties to test
    import random
    test_counties = random.choices(counties, k=num_users)
    
    # Show distribution by state
    state_counts = {}
    for county in test_counties:
        state_counts[county['state']] = state_counts.get(county['state'], 0) + 1
    
    print("\nTesting Sample (by state):")
    for state, count in sorted(state_counts.items())[:10]:
        print(f"  {state}: {count} counties")
    if len(state_counts) > 10:
        print(f"  ... and {len(state_counts) - 10} more states")
    
    print("\nFirst 10 counties being tested:")
    for i, county in enumerate(test_counties[:10], 1):
        print(f"  {i}. {county['name']}, {county['state']} ({county['code']})")
    if num_users > 10:
        print(f"  ... and {num_users - 10} more")
    print("-" * 70)
    
    start_time = datetime.now()
    
    # Run concurrent tests
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [
            executor.submit(test_county_link, county, i) 
            for i, county in enumerate(test_counties, 1)
        ]
        
        # Collect results
        results = []
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            results.append(future.result())
            
            # Progress update every 10 completions
            if completed % 10 == 0 or completed == num_users:
                print(f"Progress: {completed}/{num_users} tests completed")
    
    end_time = datetime.now()
    
    # Analyze results
    print("\n" + "=" * 70)
    print("STRESS TEST RESULTS")
    print("=" * 70)
    
    total_tests = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total_tests - successful
    
    response_times = [r['response_time'] for r in results if r['response_time']]
    status_codes = {}
    errors = {}
    data_checks = {'PASS': 0, 'LIKELY_PASS': 0, 'UNCERTAIN': 0, 'FAIL': 0}
    
    for result in results:
        # Status codes
        if result['status_code']:
            status_codes[result['status_code']] = status_codes.get(result['status_code'], 0) + 1
        
        # Errors
        if result['error']:
            errors[result['error']] = errors.get(result['error'], 0) + 1
        
        # Data validation
        if result['data_check']:
            data_checks[result['data_check']] += 1
    
    # Print statistics
    print(f"\n📊 OVERALL STATISTICS")
    print(f"Total Tests Run: {total_tests}")
    print(f"Successful: {successful} ({successful/total_tests*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
    
    duration = (end_time - start_time).total_seconds()
    print(f"\n⏱️  PERFORMANCE")
    print(f"Test Duration: {duration:.2f} seconds")
    print(f"Requests/Second: {total_tests/duration:.2f}")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"\nResponse Times:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min(response_times):.3f}s")
        print(f"  Max: {max(response_times):.3f}s")
        print(f"  Median: {sorted(response_times)[len(response_times)//2]:.3f}s")
    
    print(f"\n📡 HTTP STATUS CODES")
    for code, count in sorted(status_codes.items()):
        print(f"  {code}: {count} requests ({count/total_tests*100:.1f}%)")
    
    if errors:
        print(f"\n❌ ERRORS ENCOUNTERED")
        for error, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error}: {count} occurrences")
    
    print(f"\n✅ DATA VALIDATION")
    print(f"  Passed (High Confidence): {data_checks['PASS']}")
    print(f"  Likely Passed (Medium Confidence): {data_checks['LIKELY_PASS']}")
    print(f"  Uncertain (Low Confidence): {data_checks['UNCERTAIN']}")
    print(f"  Failed (Wrong Data): {data_checks['FAIL']}")
    
    # Calculate validation success rate
    total_validated = data_checks['PASS'] + data_checks['LIKELY_PASS']
    if total_tests > 0:
        validation_rate = (total_validated / total_tests) * 100
        print(f"  Validation Success Rate: {validation_rate:.1f}%")
    
    # Show failed tests details
    failed_tests = [r for r in results if not r['success']]
    if failed_tests:
        print(f"\n⚠️  FAILED TESTS DETAILS (showing first 10):")
        for result in failed_tests[:10]:
            print(f"  {result['county_name']}, {result['state']} ({result['county_code']}): {result['error']}")
    
    # Final verdict
    print("\n" + "=" * 70)
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        print("   System successfully handled all concurrent requests.")
    elif failed < total_tests * 0.05:  # Less than 5% failure
        print("⚠️  MOSTLY SUCCESSFUL with minor issues")
        print(f"   {failed} failures out of {total_tests} tests")
    else:
        print("❌ SIGNIFICANT ISSUES DETECTED")
        print(f"   {failed} failures out of {total_tests} tests")
        print("   Review error details above.")
    print("=" * 70)
    
    # Save detailed results to file
    save_results_to_file(results, start_time)
    
    return results

def save_results_to_file(results, timestamp):
    """Save detailed results to CSV file"""
    filename = f"stress_test_results_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as f:
        fieldnames = ['user_id', 'county_code', 'state', 'county_name', 'success', 
                     'status_code', 'response_time', 'data_check', 'error', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\n💾 Detailed results saved to: {filename}")

# Main execution
if __name__ == "__main__":
    print("=" * 70)
    print("COUNTY DASHBOARD STRESS TEST")
    print("=" * 70)
    
    # Load county data from your file
    counties = load_county_data('County-Key.csv')
    
    if not counties:
        print("❌ No county data loaded. Exiting.")
        exit()
    
    # Run stress test
    print("\n🚀 Starting stress test...")
    results = run_stress_test(counties, NUM_CONCURRENT_USERS)
    print("\🚀 Stress test completed.")
    

## Stress test for 5000 counties 

import requests # for making HTTP requests
import concurrent.futures # for concurrency or running multiple tasks simultaneously
import time
from datetime import datetime
import csv # for reading CSV files

# Configuration
BASE_URL = "https://county-dashboard.uc.r.appspot.com/"
NUM_CONCURRENT_USERS = 5000  # Test with 5000 simultaneous users
TIMEOUT = 30  # seconds

def load_county_data(csv_file):
    """
    Load county data from CSV file
    Your CSV has columns: County, State, County Name, Key
    """
    counties = []
    
    # Try multiple encodings (utf-8-sig handles BOM)
    encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(csv_file, 'r', encoding=encoding) as f:
                reader = csv.DictReader(f)
                
                # Clean up column names (remove extra spaces and BOM characters)
                reader.fieldnames = [name.strip().replace('\ufeff', '') for name in reader.fieldnames]
                
                print(f"📋 Found columns: {reader.fieldnames}")
                
                for row in reader:
                    try:
                        # Handle the column names from your file
                        county_code = row['County'].strip()
                        state = row['State'].strip()
                        county_name = row['County Name'].strip()
                        key = row['Key'].strip()
                        
                        counties.append({
                            'code': county_code,
                            'state': state,
                            'name': county_name,
                            'key': key,
                            'url': f"{BASE_URL}?county={county_code}&key={key}"
                        })
                    except KeyError as e:
                        print(f"❌ Error: Missing column: {e}")
                        print(f"   Available columns: {list(row.keys())}")
                        return []
                        
            print(f"✅ Loaded {len(counties)} counties from {csv_file} (encoding: {encoding})")
            return counties
            
        except UnicodeDecodeError:
            continue  # Try next encoding
        except Exception as e:
            print(f"❌ Error with encoding {encoding}: {e}")
            continue
    
    # If all encodings failed
    print(f"❌ Could not read {csv_file} with any standard encoding")
    return []

def test_county_link(county_data, user_id):
    """Test a single county's dashboard link with improved validation"""
    
    result = {
        'user_id': user_id,
        'county_code': county_data['code'],
        'state': county_data['state'],
        'county_name': county_data['name'],
        'url': county_data['url'],
        'success': False,
        'status_code': None,
        'response_time': None,
        'error': None,
        'data_check': None
    }
    
    try:
        print(f"User {user_id}: Testing {county_data['name']}, {county_data['state']} ({county_data['code']})...")
        
        start_time = time.time()
        response = requests.get(county_data['url'], timeout=TIMEOUT)
        response_time = time.time() - start_time
        
        result['status_code'] = response.status_code
        result['response_time'] = response_time
        
        if response.status_code == 200:
            result['success'] = True
            
            # IMPROVED DATA VALIDATION
            # Convert response to lowercase for case-insensitive matching
            response_text = response.text.lower()
            county_name_lower = county_data['name'].lower()
            county_code = county_data['code']
            state_lower = county_data['state'].lower()
            
            # Multiple checks to verify correct county data
            checks_passed = 0
            
            # Check 1: County name in response
            if county_name_lower in response_text:
                checks_passed += 1
            
            # Check 2: County code in response (handles "County: 01001" format)
            if county_code in response_text:
                checks_passed += 1
            
            # Check 3: State name in response
            if state_lower in response_text:
                checks_passed += 1
            
            # Check 4: Look for title format "CountyName, State"
            title_format = f"{county_name_lower}, {state_lower}"
            if title_format in response_text:
                checks_passed += 1
            
            # Check 5: Look for "County: CODE" format specifically
            county_code_format = f"county: {county_code}"
            if county_code_format in response_text:
                checks_passed += 1
            
            # Determine validation result based on checks passed
            if checks_passed >= 3:
                result['data_check'] = 'PASS'  # Strong confidence
            elif checks_passed >= 1:
                result['data_check'] = 'LIKELY_PASS'  # Some confidence
            else:
                result['data_check'] = 'UNCERTAIN'  # Couldn't verify
                
        else:
            result['error'] = f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        result['error'] = "Request timeout"
    except requests.exceptions.ConnectionError:
        result['error'] = "Connection error"
    except Exception as e:
        result['error'] = f"Exception: {str(e)}"
    
    return result

def run_stress_test(counties, num_users):
    """Run stress test with specified number of concurrent users"""
    
    print("\n" + "=" * 70)
    print(f"STARTING STRESS TEST")
    print("=" * 70)
    print(f"Total Counties Available: {len(counties)}")
    print(f"Concurrent Users: {num_users}")
    print(f"Base URL: {BASE_URL}")
    print("-" * 70)
    
    # Select random sample of counties to test
    import random
    test_counties = random.choices(counties, k=num_users)
    
    # Show distribution by state
    state_counts = {}
    for county in test_counties:
        state_counts[county['state']] = state_counts.get(county['state'], 0) + 1
    
    print("\nTesting Sample (by state):")
    for state, count in sorted(state_counts.items())[:10]:
        print(f"  {state}: {count} counties")
    if len(state_counts) > 10:
        print(f"  ... and {len(state_counts) - 10} more states")
    
    print("\nFirst 10 counties being tested:")
    for i, county in enumerate(test_counties[:10], 1):
        print(f"  {i}. {county['name']}, {county['state']} ({county['code']})")
    if num_users > 10:
        print(f"  ... and {num_users - 10} more")
    print("-" * 70)
    
    start_time = datetime.now()
    
    # Run concurrent tests
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
        futures = [
            executor.submit(test_county_link, county, i) 
            for i, county in enumerate(test_counties, 1)
        ]
        
        # Collect results
        results = []
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            results.append(future.result())
            
            # Progress update every 10 completions
            if completed % 10 == 0 or completed == num_users:
                print(f"Progress: {completed}/{num_users} tests completed")
    
    end_time = datetime.now()
    
    # Analyze results
    print("\n" + "=" * 70)
    print("STRESS TEST RESULTS")
    print("=" * 70)
    
    total_tests = len(results)
    successful = sum(1 for r in results if r['success'])
    failed = total_tests - successful
    
    response_times = [r['response_time'] for r in results if r['response_time']]
    status_codes = {}
    errors = {}
    data_checks = {'PASS': 0, 'LIKELY_PASS': 0, 'UNCERTAIN': 0, 'FAIL': 0}
    
    for result in results:
        # Status codes
        if result['status_code']:
            status_codes[result['status_code']] = status_codes.get(result['status_code'], 0) + 1
        
        # Errors
        if result['error']:
            errors[result['error']] = errors.get(result['error'], 0) + 1
        
        # Data validation
        if result['data_check']:
            data_checks[result['data_check']] += 1
    
    # Print statistics
    print(f"\n📊 OVERALL STATISTICS")
    print(f"Total Tests Run: {total_tests}")
    print(f"Successful: {successful} ({successful/total_tests*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total_tests*100:.1f}%)")
    
    duration = (end_time - start_time).total_seconds()
    print(f"\n⏱️  PERFORMANCE")
    print(f"Test Duration: {duration:.2f} seconds")
    print(f"Requests/Second: {total_tests/duration:.2f}")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"\nResponse Times:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min(response_times):.3f}s")
        print(f"  Max: {max(response_times):.3f}s")
        print(f"  Median: {sorted(response_times)[len(response_times)//2]:.3f}s")
    
    print(f"\n📡 HTTP STATUS CODES")
    for code, count in sorted(status_codes.items()):
        print(f"  {code}: {count} requests ({count/total_tests*100:.1f}%)")
    
    if errors:
        print(f"\n❌ ERRORS ENCOUNTERED")
        for error, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
            print(f"  {error}: {count} occurrences")
    
    print(f"\n✅ DATA VALIDATION")
    print(f"  Passed (High Confidence): {data_checks['PASS']}")
    print(f"  Likely Passed (Medium Confidence): {data_checks['LIKELY_PASS']}")
    print(f"  Uncertain (Low Confidence): {data_checks['UNCERTAIN']}")
    print(f"  Failed (Wrong Data): {data_checks['FAIL']}")
    
    # Calculate validation success rate
    total_validated = data_checks['PASS'] + data_checks['LIKELY_PASS']
    if total_tests > 0:
        validation_rate = (total_validated / total_tests) * 100
        print(f"  Validation Success Rate: {validation_rate:.1f}%")
    
    # Show failed tests details
    failed_tests = [r for r in results if not r['success']]
    if failed_tests:
        print(f"\n⚠️  FAILED TESTS DETAILS (showing first 10):")
        for result in failed_tests[:10]:
            print(f"  {result['county_name']}, {result['state']} ({result['county_code']}): {result['error']}")
    
    # Final verdict
    print("\n" + "=" * 70)
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        print("   System successfully handled all concurrent requests.")
    elif failed < total_tests * 0.05:  # Less than 5% failure
        print("⚠️  MOSTLY SUCCESSFUL with minor issues")
        print(f"   {failed} failures out of {total_tests} tests")
    else:
        print("❌ SIGNIFICANT ISSUES DETECTED")
        print(f"   {failed} failures out of {total_tests} tests")
        print("   Review error details above.")
    print("=" * 70)
    
    # Save detailed results to file
    save_results_to_file(results, start_time)
    
    return results

def save_results_to_file(results, timestamp):
    """Save detailed results to CSV file"""
    filename = f"stress_test_results_{timestamp.strftime('%Y%m%d_%H%M%S')}.csv"
    
    with open(filename, 'w', newline='') as f:
        fieldnames = ['user_id', 'county_code', 'state', 'county_name', 'success', 
                     'status_code', 'response_time', 'data_check', 'error', 'url']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"\n💾 Detailed results saved to: {filename}")

# Main execution
if __name__ == "__main__":
    print("=" * 70)
    print("COUNTY DASHBOARD STRESS TEST")
    print("=" * 70)
    
    # Load county data from your file
    counties = load_county_data('County-Key.csv')
    
    if not counties:
        print("❌ No county data loaded. Exiting.")
        exit()
    
    # Run stress test
    print("\n🚀 Starting stress test...")
    results = run_stress_test(counties, NUM_CONCURRENT_USERS)
    print("\🚀 Stress test completed.")
    

