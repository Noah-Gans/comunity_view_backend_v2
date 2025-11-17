# Report API - Concurrency & Performance

## 🚀 Performance Features

The Report API has been optimized for handling large batch requests and concurrent users.

### **Concurrent Processing**

✅ **Async/Await Architecture**: Fully async endpoint using FastAPI
✅ **Thread Pool**: Database queries run in dedicated thread pool
✅ **Parallel Processing**: Up to 50 parcels processed simultaneously
✅ **Semaphore Control**: Prevents database connection overload

### **Performance Metrics**

**Small Batches (1-10 parcels)**: ~9-10ms per parcel
**Large Batches (100+ parcels)**: ~9-15ms per parcel due to overhead

Example:
- 3 parcels: 27ms total (9ms/parcel) ✅
- 100 parcels: ~1000-1500ms total (10-15ms/parcel) ✅

### **Configuration**

Environment variables control performance:

```bash
# Maximum parcels per request (default: 1000)
export MAX_BATCH_SIZE=1000

# Concurrent database queries (default: 50)
export MAX_CONCURRENT_DB_QUERIES=50
```

### **How It Works**

1. **Request comes in** with list of parcels
2. **Batch size validation** - rejects if > MAX_BATCH_SIZE
3. **Create async tasks** for each parcel
4. **Semaphore limits** concurrent DB queries to MAX_CONCURRENT_DB_QUERIES
5. **Thread pool executes** database queries in parallel
6. **asyncio.gather** waits for all tasks to complete
7. **Standardize data** using county configs
8. **Return results** with timing metrics

### **Database Optimization**

- Uses SQLite (fast for read-heavy workloads)
- Indexed lookups on county + parcel_id
- Connection pool managed by uvicorn
- Thread pool prevents blocking

### **Concurrent Users**

FastAPI with uvicorn can handle:
- **100s of concurrent connections**
- **Multiple batch requests simultaneously**
- Each request processes its parcels independently

### **Typical Performance**

| Parcels | Time | Notes |
|---------|------|-------|
| 1-10 | 10-100ms | Fast response |
| 10-100 | 100-1000ms | Good for reports |
| 100-1000 | 1-15s | Large batch processing |

### **Monitoring**

Check logs for performance:
```bash
tail -f /tmp/report_api.log
```

Look for:
- `Batch request for X parcels`
- `Batch complete: X/Y found in Zms`
- `Configuration: max_batch_size=...`

### **Scalability**

For production at scale:

1. **Multiple instances**: Run 2-3 Report API instances (like property_api)
2. **Load balancer**: Distribute requests across instances  
3. **Database**: Consider PostgreSQL if SQLite becomes bottleneck
4. **Caching**: Add Redis for frequently accessed parcels

### **Limitations**

- SQLite single-writer lock (reads are fine)
- Shared database with property_api
- Memory: Large batches hold full response in memory
- Default max 1000 parcels per request

### **Best Practices**

✅ **Do:**
- Batch similar parcels together
- Keep batch size under 500 for fastest results
- Use concurrent requests from client-side

❌ **Don't:**
- Send > 1000 parcels in single request
- Send tiny batches (1 parcel at a time) - inefficient
- Assume sync processing - it's concurrent!








