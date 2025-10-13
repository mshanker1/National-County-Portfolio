import sqlite3
import os

print("🔍 DATABASE DIAGNOSTIC")
print("=" * 60)

# Check for database files
db_files = ['sustainability_data.db', 'county_health.db']

for db_file in db_files:
    print(f"\n📁 Checking {db_file}:")
    
    if os.path.exists(db_file):
        file_size = os.path.getsize(db_file) / (1024 * 1024)  # Convert to MB
        print(f"   ✅ File exists ({file_size:.2f} MB)")
        
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = cursor.fetchall()
            
            print(f"   📊 Tables found: {len(tables)}")
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"      • {table_name}: {count} rows")
            
            # Check for specific important tables
            important_tables = ['counties', 'raw_metrics', 'normalized_metrics', 'aggregated_scores']
            print(f"\n   🔑 Key tables check:")
            for table in important_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
                exists = cursor.fetchone() is not None
                print(f"      {'✅' if exists else '❌'} {table}")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ Error reading database: {e}")
    else:
        print(f"   ❌ File not found")
        print(f"      Expected location: {os.path.abspath(db_file)}")

print("\n" + "=" * 60)
print("💡 RECOMMENDATIONS:")
print()

if os.path.exists('sustainability_data.db'):
    print("✅ Use sustainability_data.db (this is the correct database)")
    print("   Make sure county_secure_dashboard.py uses:")
    print("   sqlite3.connect('sustainability_data.db')")
else:
    print("❌ sustainability_data.db not found!")
    print("   You need to run the data processing scripts first")

if os.path.exists('county_health.db'):
    print("\n⚠️  county_health.db exists but is the WRONG database")
    print("   This is from an old version of the code")
    print("   Delete or rename this file to avoid confusion")

print("\n📝 Current working directory:")
print(f"   {os.getcwd()}")