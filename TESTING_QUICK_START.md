# Testing Quick Start Guide

You now have **3 complete testing approaches** ready to use. Pick the one that matches what you need right now.

## 🚀 QUICK START (Pick One)

### Option 1: Local Test (30 seconds) - TEST NOW
```bash
python test_handler_local.py
```
- ✅ No Docker or API needed
- ✅ Tests all critical logic (URL parsing, status checking, base64)
- ✅ Validates handler fixes work locally
- ⏱️ Takes: ~30 seconds

**When to use:** Before any other testing, to validate your code changes locally

---

### Option 2: Docker Development (No Rebuilds!) - TEST WITH REAL API
```bash
docker-compose -f docker-compose-dev.yml up
```
- ✅ Live Fooocus API (real image generation)
- ✅ Code changes take effect immediately (NO REBUILD!)
- ✅ Volume mounts handler.py directly
- ⏱️ Takes: ~5 minutes first time, <1 second on code changes

**When to use:** After local tests pass, to verify with actual API

**Edit workflow:**
```
1. Edit handler.py in your editor
2. Save the file
3. Run your test request
4. Changes take effect immediately (no rebuild!)
```

**How to test with Docker:**
- Edit `docker-compose-dev.yml` and set the Fooocus API URL if needed
- Start: `docker-compose -f docker-compose-dev.yml up`
- In another terminal, test with curl or Python requests
- View logs: `docker-compose -f docker-compose-dev.yml logs -f`

---

### Option 3: RunPod Endpoint (Live Testing) - TEST ON YOUR POD
```bash
# First: Edit test_runpod_endpoint.py and set:
# RUNPOD_ENDPOINT = "your-pod-url"
# RUNPOD_API_KEY = "your-api-key"

python test_runpod_endpoint.py
```
- ✅ Tests against your live RunPod pod
- ✅ Full end-to-end validation
- ✅ Realistic performance metrics
- ⏱️ Takes: ~2-5 minutes per test

**When to use:** After local + Docker tests pass, before pushing to production

---

## 📋 RECOMMENDED WORKFLOW

### For Quick Iteration:
```
1. Make code changes
   ↓
2. Run: python test_handler_local.py (30s)
   ✓ Quick validation
   ↓
3. If passes, run Docker tests (no rebuild!)
   ✓ Real API validation
   ↓
4. If passes, test on live RunPod
   ✓ Production validation
   ↓
5. Commit and push when satisfied
```

### Time Breakdown:
- Local tests: 30 seconds
- Docker setup: 5 minutes (first time only)
- Docker test: <1 second (after setup)
- RunPod test: 2-5 minutes
- **Total**: Can do local + Docker + RunPod in ~10 minutes

---

## 🔧 WHAT WAS CREATED

### test_handler_local.py
Local unit tests with mocked responses:
- `test_url_parsing()` - HTTP URLs → file paths
- `test_status_value_checking()` - Status checking logic
- `test_base64_encoding()` - Image encoding
- `test_handler_logic()` - Response format detection

Run: `python test_handler_local.py`

### docker-compose-dev.yml
Docker development environment:
- Volume mounts handler.py directly
- No rebuild needed on code changes
- Pre-configured with defaults
- Ready to use with your Fooocus API

Run: `docker-compose -f docker-compose-dev.yml up`

### test_runpod_endpoint.py
RunPod integration tests:
- Test simple generation
- Test multiple images
- Test error handling
- Validate response format

Run: `python test_runpod_endpoint.py` (after configuring)

---

## 🐛 CRITICAL BUGS FIXED

Both of these issues are now solved in handler.py (Commit 83418d8):

### Bug #1: Task Status Value ✅ FIXED
**Problem**: Handler was checking for "success", but API returns "finished"  
**Solution**: Fixed status check to `status == "finished"`  
**Code**: handler.py lines 140-155

### Bug #2: Response URL Format ✅ FIXED
**Problem**: Handler tried to open HTTP URLs as file paths  
**Solution**: Added `parse_api_url_to_filepath()` to convert URLs  
**Code**: handler.py lines 321-368

---

## ❓ TROUBLESHOOTING

### Local tests fail
- Check Python 3.8+ is installed
- Check PIL is available: `python -c "import PIL; print(PIL.__version__)"`
- Run with: `python -u test_handler_local.py` for unbuffered output

### Docker tests fail
- Check Docker is running: `docker --version`
- Check port 7866 isn't already in use: `lsof -i :7866`
- Check Fooocus API URL is correct in docker-compose-dev.yml
- View logs: `docker-compose -f docker-compose-dev.yml logs -f`

### RunPod tests can't reach endpoint
- Verify RUNPOD_ENDPOINT is set correctly in test_runpod_endpoint.py
- Check your RunPod pod status (should show "Running")
- Verify your API key is correct
- Test connectivity: `curl https://your-pod-url/api` in terminal

### Handler still timing out
- Local tests validate status checking is correct
- Docker tests validate with real API
- If both pass but RunPod times out, pod may be too slow
- Check RunPod pod disk usage and memory

---

## 📊 TESTING DECISION TREE

```
Want to test quickly?
  → Use Local Tests (30s)
    
Want to test with real API but fast?
  → Use Docker Volume Mount (no rebuild)
    
Want full integration test?
  → Use RunPod Endpoint Tests (2-5m)

Want all three? 
  → Do local → docker → runpod in ~10 minutes total
```

---

## 🎯 NEXT STEPS

1. **Right now**: `python test_handler_local.py`
   - Takes 30 seconds
   - Validates all critical fixes work

2. **After local passes**: `docker-compose -f docker-compose-dev.yml up`
   - Takes 5 minutes first time
   - Tests with actual Fooocus API
   - No Docker rebuild on code changes!

3. **After Docker passes**: `python test_runpod_endpoint.py`
   - Configure with your pod URL/API key
   - Full integration test on live pod

4. **When satisfied**: Commit and push
   - All critical bugs are fixed
   - All tests pass
   - Ready for production

---

## 📚 RELATED FILES

- **DEVELOPMENT_TESTING_GUIDE.md** - Detailed explanation of all approaches
- **handler.py** - Your main handler code (Commit 83418d8 with fixes)
- **test_handler_local.py** - Local unit tests
- **test_runpod_endpoint.py** - RunPod integration tests
- **docker-compose-dev.yml** - Development Docker configuration

---

## ✨ KEY ADVANTAGES

### Local Testing
- Instant feedback (30s)
- No network required
- No Docker required
- No API key needed
- Perfect for rapid iteration

### Docker Development
- Test with real API
- No Docker rebuild
- Code hot-reload
- Realistic image generation
- Fast iteration cycle

### RunPod Testing
- Test on your actual pod
- Real performance metrics
- Validate all integrations
- Catch pod-specific issues
- Production-like environment

---

**Status: All testing options ready to use!**

Start with `python test_handler_local.py` right now for quick validation.
