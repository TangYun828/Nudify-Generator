# Fooocus API Parameters Reference

## ✅ Validated API Parameters (from apis/models/requests.py)

Based on the CommonRequest model in `apis/models/requests.py` and production testing, here are the CORRECT parameters for matching Fooocus UI quality:

### 🎯 THE SECRET: Style Selections

**This is the #1 reason API images look different from UI images!**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| **style_selections** | array | ["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"] | **CRITICAL!** Wraps prompts with hidden templates |

- **Fooocus V2**: Uses GPT-2 model to expand prompts with descriptive detail
- **Fooocus Enhance**: Adds contrast and lighting improvements  
- **Fooocus Sharp**: Adds fine textures and detail

**Without these styles, images will look flat and generic!**

### Core Quality Parameters

| Parameter | Type | Recommended | Range | Description |
|-----------|------|-------------|-------|-------------|
| **guidance_scale** | float | **4.0** | 1.0 - 30.0 | **Use 4.0 for realistic skin!** Higher values (7+) cause oversaturation |
| **sharpness** | float | 2.0 - 5.0 | 0.0 - 30.0 | 2.0 = balanced, 5.0 = HD look. Above 10 causes artifacts |
| **performance_selection** | string | "Quality" | Speed/Quality | Quality = 60 steps (paid), Speed = 30 steps (free) |
| **aspect_ratios_selection** | string | "832*1216" | Various ratios | Best for vertical portraits |
| **image_seed** | int | -1 | Any int | Always use -1 for random |
| **sampler_name** | string | "dpmpp_2m_sde_gpu" | See sampler list | Sampling algorithm |
| **scheduler_name** | string | "karras" | See scheduler list | Noise scheduling method |
| **overwrite_step** | int | -1 | Any int | Custom sampling steps (-1 = auto based on performance) |

### Default Values from modules/config.py

```python
default_cfg_scale = 7.0  # ⚠️ API default, but use 4.0 for realistic results!
default_sample_sharpness = 2.0  
default_sampler = 'dpmpp_2m_sde_gpu'
default_scheduler = 'karras'
default_aspect_ratio = '1152*896'  # Or use '832*1216' for portraits
default_overwrite_step = -1  # -1 means auto-determine based on performance_selection
default_styles = ["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"]  # CRITICAL!
```

### Performance Modes

The `performance_selection` parameter determines base quality settings:

- **"Speed"**: ~30 steps, optimized for fast generation
- **"Quality"**: ~60 steps, balanced quality/speed (recommended)
- **"Extreme Speed"**: Minimal steps, fastest generation

When `overwrite_step = -1`, the system automatically chooses steps based on performance mode.
When `overwrite_step > 0`, it overrides the automatic step count.

## 🔧 Parameter Name Corrections

### ❌ INCORRECT → ✅ CORRECT

| Used in handler.py | Actual API Parameter | Notes |
|--------------------|---------------------|-------|
| ~~sampling_steps~~ | **overwrite_step** | Used to override automatic step count |
| steps | **overwrite_step** | Both work, but overwrite_step is canonical |

## 📝 Complete Example Payload (Production-Optimized)

```json
{
  "prompt": "high quality photo of a beautiful woman, cinematic lighting",
  "negative_prompt": "child, underage, loli, shota, deformed, watermark, low quality",
  "base_model_name": "onlyfornsfw118_v20.safetensors",
  "aspect_ratios_selection": "832*1216",
  "image_number": 1,
  "output_format": "png",
  "async_process": false,
  "stream_output": false,
  
  "performance_selection": "Quality",
  "style_selections": ["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"],
  "guidance_scale": 4.0,
  "sharpness": 2.0,
  "image_seed": -1,
  
  "sampler_name": "dpmpp_2m_sde_gpu",
  "scheduler_name": "karras",
  "refiner_model_name": "None",
  "refiner_switch": 0.5,
  "loras": []
}
```

### Python Client Example

```python
import requests

payload = {
    "prompt": "high quality photo of a beautiful woman, cinematic lighting",
    "negative_prompt": "child, underage, loli, shota, deformed, watermark",
    "style_selections": ["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"],
    "performance_selection": "Quality",
    "aspect_ratios_selection": "832*1216",
    "sharpness": 2.0,
    "guidance_scale": 4.0,
    "image_number": 1,
    "image_seed": -1
}

response = requests.post(
    "http://your-api:8888/v1/engine/generate/",
    json=payload,
    timeout=300
)
result = response.json()
```

## 🎨 Available Samplers (from modules/flags.py)

Common high-quality samplers:
- `dpmpp_2m_sde_gpu` - Recommended for quality (GPU accelerated)
- `dpmpp_2m_sde` - CPU version of above
- `euler_ancestral` - Classic, good for artistic styles
- `dpm_2` - Fast with good quality
- `ddim` - Deterministic, good for consistency

## 📅 Available Schedulers

- `karras` - Recommended, smoother transitions (default)
- `normal` - Standard scheduling
- `exponential` - Faster convergence
- `simple` - Minimal processing

## 🖼️ Aspect Ratio Options

Standard ratios available:
- `1152*896` - Landscape (default, 1.29:1)
- `896*1152` - Portrait (0.78:1)
- `1216*832` - Wide landscape (1.46:1)
- `832*1216` - Tall portrait (0.68:1)
- `1344*768` - Cinematic (1.75:1)
- `768*1344` - Tall cinematic (0.57:1)
- `1024*1024` - Square (1:1)

## 🔍 Quality Optimization Tips

### For Maximum Quality (Paid Tier):
```json
{
  "style_selections": ["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"],
  "performance_selection": "Quality",
  "guidance_scale": 4.0,
  "sharpness": 3.0,
  "overwrite_step": 80,
  "aspect_ratios_selection": "832*1216",
  "sampler_name": "dpmpp_2m_sde_gpu",
  "scheduler_name": "karras"
}
```

### For Balanced Quality/Speed (Recommended):
```json
{
  "style_selections": ["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"],
  "performance_selection": "Quality",
  "guidance_scale": 4.0,
  "sharpness": 2.0,
  "overwrite_step": 60,
  "aspect_ratios_selection": "832*1216",
  "sampler_name": "dpmpp_2m_sde_gpu",
  "scheduler_name": "karras"
}
```

### For Fast Generation (Free Tier):
```json
{
  "style_selections": ["Fooocus V2"],
  "performance_selection": "Speed",
  "guidance_scale": 4.0,
  "sharpness": 1.5,
  "overwrite_step": -1,
  "aspect_ratios_selection": "1024*1024",
  "sampler_name": "euler_ancestral",
  "scheduler_name": "normal"
}
```

## 🚨 Critical Production Notes

### 1. **ALWAYS Include style_selections**
This is the #1 reason API images look worse than UI:
- ❌ Without styles: Flat, generic, "plastic" skin
- ✅ With styles: Professional, detailed, cinematic

**Rule**: Never send a request without `["Fooocus V2", "Fooocus Enhance", "Fooocus Sharp"]`

### 2. **Guidance Scale: 4.0 vs 7.0+**
- **4.0**: Realistic skin tones, natural lighting (recommended for NSFW)
- **7.0+**: Oversaturated, "deep-fried" look, unnatural colors
- API default is 7.0, but **always override to 4.0** for realistic results

### 3. **Sharpness Sweet Spots**:
- **2.0**: Balanced, natural detail (default)
- **3.0-5.0**: HD look, more texture (for "crisp" images)
- **10.0+**: Artifacts, over-sharpening (avoid)

### 4. **Performance Tiers**:
- **Quality (60 steps)**: Paid tier, professional results
- **Speed (30 steps)**: Free tier, may look "plastic"
- Steps have linear time impact: 60 steps ≈ 2x time vs 30 steps

### 5. **Aspect Ratio Best Practices**:
- **832*1216**: Best for vertical portraits (character focus)
- **1152*896**: Landscape/wide shots
- **1024*1024**: Square (worst quality, avoid if possible)

### 6. **Backend Safety Enforcement**:
Hardcode negative prompt on server to prevent user tampering:
```python
safety_negative = "child, underage, loli, shota, toddler, baby, minor"
full_negative = f"{user_negative}, {safety_negative}"
```

### 7. **Deployment Flags** (from launch.py):
```bash
--host 0.0.0.0          # Allow external connections
--port 8888             # Custom port
--base-url http://...   # For reverse proxy/webhooks
--nowebui               # API-only mode
```

## 📊 API Endpoint

```
POST /v1/engine/generate/
Content-Type: application/json
```

Full API route defined in: `apis/routes/generate.py`
Request model defined in: `apis/models/requests.py` (CommonRequest class)
Default configs in: `modules/config.py`

## 🔗 Related Files

- **API Route**: [apis/routes/generate.py](apis/routes/generate.py)
- **Request Model**: [apis/models/requests.py](apis/models/requests.py)  
- **Config Defaults**: [modules/config.py](modules/config.py)
- **Handler Implementation**: [handler.py](handler.py)

---

*Last updated: 2025-01-26*
*Source: Fooocus API codebase analysis*
