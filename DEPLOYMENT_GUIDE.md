# Google Cloud / BigQuery Deployment Guide

Complete step-by-step instructions for deploying the County Sustainability Portfolio to Google Cloud Platform.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Project Setup](#google-cloud-project-setup)
3. [BigQuery Database Setup](#bigquery-database-setup)
4. [Google App Engine Deployment](#google-app-engine-deployment)
5. [Testing and Verification](#testing-and-verification)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

1. **Google Cloud SDK (gcloud CLI)**
   - Download from: https://cloud.google.com/sdk/docs/install
   - After installation, verify with:
     ```bash
     gcloud --version
     ```

2. **Python 3.12**
   - Check your version:
     ```bash
     python3 --version
     ```

3. **Google Cloud Account**
   - Sign up at: https://cloud.google.com/
   - Enable billing (required for App Engine and BigQuery)

### Required Files

Ensure you have these files in your project directory:
- `National_County_Dashboard.csv` - Main data file
- `County-Key.csv` - County authentication keys
- `display_names.csv` - Display name mappings
- `county_secure_dashboard.py` - Main application
- `enhanced_radar_v2_with_fast_state.py` - BigQuery data provider
- `stage1_database_loader.py` - Database loading script
- `stage2_normalization.py` - Normalization script
- `requirements.txt` - Python dependencies
- `app.yaml` - App Engine configuration

---

## Google Cloud Project Setup

### Step 1: Initialize Google Cloud SDK

1. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   ```
   This will open a browser window for authentication.

2. **Set your project ID:**
   ```bash
   # Replace 'county-portfolio' with your desired project ID
   export PROJECT_ID="county-portfolio"
   gcloud config set project $PROJECT_ID
   ```

   If the project doesn't exist yet, create it:
   ```bash
   gcloud projects create $PROJECT_ID --name="County Sustainability Portfolio"
   gcloud config set project $PROJECT_ID
   ```

3. **Link billing account:**
   ```bash
   # List available billing accounts
   gcloud billing accounts list

   # Link billing to your project (replace BILLING_ACCOUNT_ID)
   gcloud billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
   ```

### Step 2: Enable Required APIs

```bash
# Enable BigQuery API
gcloud services enable bigquery.googleapis.com

# Enable App Engine API
gcloud services enable appengine.googleapis.com

# Enable Cloud Build API (for deployments)
gcloud services enable cloudbuild.googleapis.com
```

### Step 3: Set Default Region

```bash
# Set your preferred region (e.g., us-central1)
gcloud config set compute/region us-central1
```

---

## BigQuery Database Setup

### Overview: Required Tables

**Total tables to create: 8**

You will create **8 BigQuery tables** across 3 stages:

| Stage | Tables Created | Count | Description |
|-------|---------------|-------|-------------|
| **Stage 1** | `counties`<br>`raw_metrics`<br>`raw_metrics_wide` | 3 | County metadata and raw data from CSV |
| **Stage 2** | `metric_statistics`<br>`normalized_metrics`<br>`aggregated_scores` | 3 | Percentile calculations and normalized scores |
| **Stage 3** | `state_percentiles`<br>`state_aggregated_scores` | 2 | State-level comparison data |

**Total Storage:** Approximately 50-100 MB for all tables combined.

---

### Step 1: Create BigQuery Dataset

```bash
# Create the main dataset (container for all 8 tables)
bq mk --dataset --location=US ${PROJECT_ID}:county_data
```

### Step 2: Upload Data to BigQuery

#### Option A: Run Stage 1 Database Loader (Recommended)

1. **Set environment variables:**
   ```bash
   export BIGQUERY_PROJECT=$PROJECT_ID
   export BIGQUERY_DATASET="county_data"
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run Stage 1 loader:**
   ```bash
   python3 stage1_database_loader.py
   ```

   This will:
   - Parse `National_County_Dashboard.csv`
   - Create `counties` table (county metadata)
   - Create `raw_metrics` table (long format)
   - Create `raw_metrics_wide` table (wide format)

   **Expected output:**
   ```
   ✅ Created counties table (3144 rows)
   ✅ Created raw_metrics table
   ✅ Created raw_metrics_wide table
   ```

#### Option B: Manual Upload (Alternative)

If the script fails, you can manually upload using the BigQuery console:

1. Go to: https://console.cloud.google.com/bigquery
2. Select your project → `county_data` dataset
3. Click "CREATE TABLE"
4. Source: Upload from file → select `National_County_Dashboard.csv`
5. Configure schema detection: Auto-detect

### Step 3: Run Stage 2 Normalization

```bash
python3 stage2_normalization.py
```

This will:
- Compute percentile ranks for all metrics
- Handle reverse metrics (lower = better)
- Create `metric_statistics` table
- Create `normalized_metrics` table
- Create `aggregated_scores` table

**Expected output:**
```
✅ Created metric_statistics table
✅ Created normalized_metrics table
✅ Created aggregated_scores table (3144 counties, 15 sub-measures)
```

### Step 4: Run Stage 3 State Comparisons

```bash
python3 enhanced_radar_v2_with_fast_state.py
```

Or import and run the Stage 3 builder:
```python
from enhanced_radar_v2_with_fast_state import build_stage3_state_percentiles

# This function is at the bottom of enhanced_radar_v2_with_fast_state.py
build_stage3_state_percentiles(project_id=PROJECT_ID, dataset_id="county_data")
```

This creates:
- `state_percentiles` table (state-level percentile ranks)
- `state_aggregated_scores` table (state-level aggregated scores)

### Step 5: Verify BigQuery Tables

Check that all 8 tables were created:
```bash
bq ls ${PROJECT_ID}:county_data
```

**Expected tables (8 total):**

#### Stage 1 Tables (3):
1. **`counties`** - County metadata (FIPS, name, state) - 3,144 rows
2. **`raw_metrics`** - Raw metric values in long format - ~258,000 rows
3. **`raw_metrics_wide`** - Raw metric values in wide format - 3,144 rows

#### Stage 2 Tables (3):
4. **`metric_statistics`** - Statistical info for each metric (min, max, percentiles) - 82 rows
5. **`normalized_metrics`** - Percentile-ranked values for all metrics - ~258,000 rows
6. **`aggregated_scores`** - Sub-measure scores (15 sub-measures per county) - 3,144 rows

#### Stage 3 Tables (2):
7. **`state_percentiles`** - State-level percentile ranks - ~160,000 rows
8. **`state_aggregated_scores`** - State-level aggregated scores - ~160,000 rows

**Verification command:**
```bash
# Count tables (should return 8)
bq ls ${PROJECT_ID}:county_data | wc -l

# Check row counts
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM \`${PROJECT_ID}.county_data.counties\`"
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM \`${PROJECT_ID}.county_data.aggregated_scores\`"
```

**Expected row counts:**
- `counties`: 3,144 (one per county)
- `aggregated_scores`: 3,144 (one per county)

---

## Google App Engine Deployment

### Step 1: Review app.yaml Configuration

Open `app.yaml` and verify the configuration:

```yaml
runtime: python312
instance_class: F2

env_variables:
  BIGQUERY_PROJECT: "your-project-id"  # ← UPDATE THIS
  BIGQUERY_DATASET: "county_data"

automatic_scaling:
  target_cpu_utilization: 0.65
  min_instances: 0
  max_instances: 10
```

**Update the `BIGQUERY_PROJECT` value** to match your project ID.

### Step 2: Initialize App Engine

```bash
# Create App Engine application (one-time setup)
gcloud app create --region=us-central
```

Choose a region close to your users (e.g., `us-central` or `us-east1`).

### Step 3: Deploy to App Engine

```bash
gcloud app deploy app.yaml
```

This will:
1. Install dependencies from `requirements.txt`
2. Build a Docker container
3. Deploy to App Engine
4. Assign a URL: `https://PROJECT_ID.uc.r.appspot.com`

**Deployment time:** 5-10 minutes on first deploy.

### Step 4: View Deployment Status

```bash
# Check deployment status
gcloud app versions list

# View application logs
gcloud app logs tail -s default
```

---

## Testing and Verification

### Step 1: Access the Application

Your application will be available at:
```
https://PROJECT_ID.uc.r.appspot.com/?county=01001&key=autauga2024
```

**Test URLs:**
- Autauga County, AL: `?county=01001&key=autauga2024`
- Any county with master password: `?county=01001&key=county_dashboard_2024`

### Step 2: Verify BigQuery Mode

Check the application logs:
```bash
gcloud app logs tail -s default
```

You should see:
```
🔒 SECURE COUNTY SUSTAINABILITY PORTFOLIO - BIGQUERY MODE
✅ Connected to BigQuery (Stage 3/3)
   Project: your-project-id
```

### Step 3: Test Key Features

1. **Authentication**: Try accessing with correct/incorrect passwords
2. **Data Loading**: Verify county data loads correctly
3. **State/National Toggle**: Switch between comparison modes
4. **Population Rank**: Check that rank updates when switching modes
5. **Drill-down**: Click sub-measures to view detailed metrics

### Step 4: Performance Testing

Monitor application performance:
```bash
# View real-time logs
gcloud app logs tail -s default --level=info

# Check instance usage
gcloud app instances list
```

---

## Troubleshooting

### Issue: "Permission Denied" Errors

**Solution:**
```bash
# Grant BigQuery permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### Issue: "Module not found" during deployment

**Solution:** Ensure `requirements.txt` includes all dependencies:
```bash
# Regenerate requirements.txt
pip freeze > requirements.txt
```

### Issue: Deployment exceeds quota

**Solution:** Request quota increase:
1. Go to: https://console.cloud.google.com/iam-admin/quotas
2. Search for "App Engine"
3. Request increase for instances/memory

### Issue: BigQuery table not found

**Solution:** Verify table names match the code:
```bash
bq show ${PROJECT_ID}:county_data.aggregated_scores
```

If missing, re-run the stage scripts:
```bash
python3 stage1_database_loader.py
python3 stage2_normalization.py
```

### Issue: Application is slow

**Solutions:**
1. **Increase instance class** in `app.yaml`:
   ```yaml
   instance_class: F4  # More powerful instance
   ```

2. **Adjust auto-scaling**:
   ```yaml
   automatic_scaling:
     min_instances: 1  # Keep one instance warm
     max_instances: 20
   ```

3. **Enable caching** (add to code):
   ```python
   @functools.lru_cache(maxsize=1000)
   def get_county_metrics(county_fips):
       # ... existing code
   ```

### Issue: Out of memory errors

**Solution:** Increase instance class in `app.yaml`:
```yaml
instance_class: F4  # 512MB RAM
# or
instance_class: F4_1G  # 1GB RAM
```

---

## Cost Optimization

### Estimated Monthly Costs

- **BigQuery Storage:** ~$0.02/GB/month (≈$0.10 for this dataset)
- **BigQuery Queries:** ~$5/TB processed (≈$1-5/month for moderate usage)
- **App Engine:** ~$0.05/hour per F2 instance (≈$10-50/month depending on traffic)

**Total estimated cost:** $10-60/month for moderate usage

### Cost Reduction Tips

1. **Use minimum instances wisely:**
   ```yaml
   min_instances: 0  # Scale to zero when not in use
   ```

2. **Implement request caching** to reduce BigQuery queries

3. **Use smaller instance class** for low traffic:
   ```yaml
   instance_class: F1  # 256MB RAM
   ```

4. **Set up budget alerts:**
   ```bash
   gcloud billing budgets create \
     --billing-account=BILLING_ACCOUNT_ID \
     --display-name="County Portfolio Budget" \
     --budget-amount=50
   ```

---

## Updating the Application

### Update Code Only

```bash
gcloud app deploy app.yaml
```

### Update Data Only

```bash
# Re-run data pipeline
python3 stage1_database_loader.py
python3 stage2_normalization.py
```

### Full Update (Code + Data)

```bash
# 1. Update data in BigQuery
python3 stage1_database_loader.py
python3 stage2_normalization.py

# 2. Deploy updated application
gcloud app deploy app.yaml
```

---

## Monitoring and Logs

### View Application Logs

```bash
# Real-time logs
gcloud app logs tail -s default

# Filter by severity
gcloud app logs tail -s default --level=error

# View logs in console
gcloud app browse --logs
```

### Set Up Monitoring

1. Go to: https://console.cloud.google.com/monitoring
2. Create dashboard for:
   - Request latency
   - Error rate
   - Instance count
   - BigQuery query costs

---

## Security Considerations

### 1. Secure Password Management

The current implementation uses hardcoded passwords in `COUNTY_PASSWORDS` dict. For production:

**Option A: Environment Variables**
```yaml
# In app.yaml
env_variables:
  MASTER_PASSWORD: "your-secret-password"
```

**Option B: Secret Manager**
```bash
# Store passwords in Secret Manager
gcloud secrets create master-password --data-file=password.txt

# Grant access
gcloud secrets add-iam-policy-binding master-password \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2. Enable HTTPS Only

App Engine uses HTTPS by default, but verify:
```yaml
# In app.yaml
handlers:
- url: /.*
  script: auto
  secure: always  # ← Forces HTTPS
```

### 3. IP Whitelisting (Optional)

Restrict access to specific IPs:
```yaml
# In app.yaml
handlers:
- url: /.*
  script: auto
  login: admin  # Requires Google account login
```

---

## Support and Resources

- **Google Cloud Documentation:** https://cloud.google.com/docs
- **BigQuery Documentation:** https://cloud.google.com/bigquery/docs
- **App Engine Documentation:** https://cloud.google.com/appengine/docs
- **Pricing Calculator:** https://cloud.google.com/products/calculator

---

## Quick Reference Commands

```bash
# View deployment status
gcloud app describe

# View current version
gcloud app versions list

# Stop serving traffic to old versions
gcloud app versions stop VERSION_ID

# Delete old versions
gcloud app versions delete VERSION_ID

# View application URL
gcloud app browse

# View billing
gcloud billing accounts list
gcloud billing projects describe $PROJECT_ID

# SSH into instance (for debugging)
gcloud app instances ssh INSTANCE_NAME
```

---

## Next Steps

After successful deployment:

1. ✅ Test all county authentications
2. ✅ Monitor performance for first week
3. ✅ Set up budget alerts
4. ✅ Configure custom domain (optional)
5. ✅ Enable Cloud CDN for faster loading (optional)
6. ✅ Set up automated backups of BigQuery data

---

**Deployment Date:** March 26, 2026
**Last Updated:** March 26, 2026
**Version:** 1.0
