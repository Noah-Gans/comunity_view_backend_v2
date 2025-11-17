# Daily Update Pipeline

Automated daily pipeline that:
1. Downloads fresh ownership data from county sources
2. Validates data quality (compares with previous run)
3. Uploads validated data to GCS
4. Generates PMTiles for Martin tile server
5. Regenerates search index
6. Restarts Martin and Search API
7. Sends email notification with validation report

## Setup

### 1. Configure Email (required for notifications)

Edit `daily_update_pipeline.sh` lines 23-26:
```bash
EMAIL_TO="your-email@gmail.com"
EMAIL_FROM="your-email@gmail.com"
SMTP_USER="your-email@gmail.com"
SMTP_PASS="your-gmail-app-password"
```

**Get Gmail App Password:**
1. Go to Google Account settings
2. Security → 2-Step Verification → App passwords
3. Generate password for "Mail"
4. Use that password in `SMTP_PASS`

### 2. Set Up Cron Job

```bash
# Run at 2 AM daily
./scripts/setup_cron.sh
```

**Change schedule:**
```bash
crontab -e
# Edit: 0 2 * * * → 0 14 * * * (for 2 PM)
```

## Manual Usage

```bash
# Run full pipeline manually
./scripts/daily_update_pipeline.sh

# View logs (real-time)
tail -f scripts/daily_update.log
tail -f scripts/cron.log
```

## What Gets Updated

### Data Flow:
```
1. Download → pipelines/pmtiles/final_parcels/
2. Validate → pipelines/pmtiles/validation_report.txt
3. Upload → GCS bucket
4. Generate → backend/tiles/combined_ownership.pmtiles
5. Backup → backend/tiles/combined_ownership.pmtiles.backup.TIMESTAMP
6. Update → martin_config.yaml
7. Restart → Martin (port 9000)
8. Regenerate → services/search_api/search_index.json
9. Reload → Search API (port 9001)
```

### Backups Created:
- ✅ Old GeoJSONs: `pipelines/pmtiles/final_parcels_previous/`
- ✅ Old tiles: `tiles/combined_ownership.pmtiles.backup.TIMESTAMP` (keeps last 3)
- ✅ Old config: `martin_config.yaml.backup.TIMESTAMP`

## Validation & Safety

### Automatic Validation:
- Compares new data with previous run
- **Threshold:** ≥5% change = FAIL
- **On failure:**
  - ❌ Blocks upload/tiles
  - 🔄 Auto-rollback to previous good data
  - 📧 Sends error email with validation report

### Manual Rollback:
```bash
# Restore previous GeoJSONs
cd pipelines/pmtiles
rm -rf final_parcels/
mv final_parcels_previous/ final_parcels/

# Restore previous tiles
cd tiles
mv combined_ownership.pmtiles.backup.TIMESTAMP combined_ownership.pmtiles
# Then restart Martin
```

## Service Dependencies

**The script handles services gracefully:**

| Service | If Not Running | Behavior |
|---------|---------------|----------|
| Martin | Not installed | ⚠️ Warning, continues (config updated for manual start) |
| Martin | Was running | ✅ Restarts automatically |
| Martin | Fails to start | ⚠️ Warning, continues (can start manually) |
| Search API | Not running | ⚠️ Warning, continues (will load new index on next start) |
| Search API | Running | ✅ Reloads automatically |

**Bottom line:** The pipeline generates new data/tiles even if services aren't running. You can start services later and they'll load the new data.

## Email Notifications

### Success Email Includes:
- ✅ Validation report (shows data quality)
- ✅ Duration
- ✅ Disk usage
- ✅ Martin server health
- ✅ Search API health
- 📎 Attached: `daily_update.log`

### Error Email Includes:
- ❌ Error message
- ❌ Validation report (if validation failed)
- 📎 Attached: `daily_update.log`
- 📋 Last 20 lines of log

## Troubleshooting

### Check if cron is running:
```bash
crontab -l  # View scheduled jobs
```

### View recent logs:
```bash
tail -50 scripts/daily_update.log
tail -50 scripts/cron.log
```

### Test email notifications:
```bash
cd scripts
python3 send_notification.py success \
  your-email@gmail.com \
  your-email@gmail.com \
  your-email@gmail.com \
  your-app-password \
  daily_update.log \
  300 \
  "Test message"
```

### Manually run individual steps:
```bash
# Just process & validate (no upload/tiles)
cd pipelines/pmtiles
python3 main.py --process --validate

# Just upload
python3 main.py --upload

# Just generate tiles
python3 main.py --generate-tiles
```









