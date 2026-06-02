# Carousel Export Techniques — Instagram Publishing

**Date:** 2026-05-28
**Context:** Claude Opus 4.8 carousel export, Neon Shell v2.0
**Key Insight:** Export at native resolution with proper CSS font scaling — never upscale.

---

## The Problem

The carousel is designed as an Instagram feed preview (`.feed` with `max-width: 600px`). Exporting at Instagram's native 1080x1350 resolution produces blurry output because:

1. **CSS `clamp()` caps font sizes** at values appropriate for ~600px wide feeds (e.g., title max 34px). At 1080px, fonts render at the clamp max, which is too small for the canvas creating lots of empty space.
2. **Upscaling** from 583px (natural feed width) to 1080px introduces quality loss.
3. **The slide border** (1px on `.ig-slide`) adds 1px to each dimension (1081x1351 instead of 1080x1350).

---

## The Solution: Two Export Strategies

### Strategy A: Native 1080x1350 (Instagram Direct)

Render the feed at the target width and override clamp max values via CSS injection.

```js
// 1. Set viewport wide enough
await page.setViewportSize({ width: 1400, height: 1800 });

// 2. Override font clamp max values for 1080px canvas
await page.evaluate(() => {
  const style = document.createElement('style');
  style.textContent = `
    .s1-title       { font-size: clamp(26px, 5.5vw, 56px) !important; }
    .slide-heading  { font-size: clamp(20px, 4.5vw, 50px) !important; }
    .body-p         { font-size: clamp(12px, 2.5vw, 30px) !important; }
    .s1-subtitle    { font-size: clamp(13px, 2.5vw, 28px) !important; }
    .s1-tldr        { font-size: clamp(11px, 2.2vw, 24px) !important; }
    .cta-title      { font-size: clamp(20px, 4.5vw, 52px) !important; }
    .cta-body       { font-size: clamp(12px, 2.4vw, 30px) !important; }
    .feature-title  { font-size: clamp(11px, 2.2vw, 28px) !important; }
    .feature-body   { font-size: clamp(10px, 2vw, 24px) !important; }
    .stat-number    { font-size: clamp(18px, 4vw, 42px) !important; }
    .insight-card   { font-size: clamp(11px, 2.2vw, 26px) !important; }
    .slide-content  { padding: 52px 40px 44px !important; }
    .slide-1-content { padding: 44px 40px 68px !important; }
    /* Larger watermark for export */
    .creator-watermark       { padding: 10px 18px 10px 10px !important; gap: 12px !important; }
    .creator-watermark-avatar { width: 36px !important; height: 36px !important; border-width: 2px !important; }
    .creator-watermark-name  { font-size: 14px !important; max-width: 160px !important; }
    .creator-watermark-handle { font-size: 12px !important; max-width: 160px !important; }
  `;
  document.head.appendChild(style);

  // 3. Widen feed to fit 1080px slides
  const feed = document.querySelector('.feed');
  feed.style.maxWidth = 'none';
  feed.style.width = '1150px';  // 1080 + padding
  feed.style.padding = '0 35px';

  // 4. Force slides to exactly 1080x1350
  document.querySelectorAll('.ig-slide-inner').forEach(el => {
    el.style.width = '1080px';
    el.style.height = '1350px';
  });
});

// 5. Screenshot each .ig-slide-inner at quality 100
await slide.screenshot({ path: filePath, type: 'jpeg', quality: 100 });
```

**Crop the 1px border artifact:**
```python
from PIL import Image
img = Image.open(path)
w, h = img.size
if (w, h) != (1080, 1350):
    img = img.crop(((w-1080)//2, (h-1350)//2, (w-1080)//2+1080, (h-1350)//2+1350))
    img.save(path, 'JPEG', quality=100)
```

**Typical output:** 475-846KB per slide at quality 100.

### Strategy B: 2x Retina (2160x2700 for Archive/Full HD)

Same as Strategy A but create a new browser context with `deviceScaleFactor: 2`.

```js
const hdCtx = await browser.newContext({ deviceScaleFactor: 2 });
const hdPage = await hdCtx.newPage();
// ... same CSS injection and feed widening ...
await slide.screenshot({ path: fp, type: 'jpeg', quality: 100, scale: 'device' });
```

**Typical output:** 1.0-2.4MB per slide at 2160x2700.

---

## What NOT to Do

| Approach | Result |
|----------|--------|
| Upscale 583px → 1080px via PIL | Blurry, visible quality loss (179-367KB) |
| Force 1080px width without clamp override | Small fonts, too much empty space |
| Use `scale: 'css'` with deviceScaleFactor | Ignores device scale, output at 1x |
| Screenshot `.ig-slide` instead of `.ig-slide-inner` | Includes border and box-shadow artifacts |
| Export via backend agent's carousel.html (old style) | Loses Neon Shell visual identity |

---

## Instagram Caption Template

```
pedromarins.ai <hook sentence about the topic>

<2-3 sentences of value, key stats>

<1 sentence CTA>

<engagement question>

#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5
```

**Rules:**
- No em dashes (never use `—` or `–`)
- Max 2-3 lines per paragraph
- Portuguese: informal but professional, direct
- Swipe prompt on slide 1 footer (`Deslize →`)

---

## File Organization

```
frontend/public/carousel-{topic}/
├── index.html              # Instagram feed preview (design source)
├── slide_1.jpg .. 4.jpg    # Original GPT Images 2.0 (1792x1024)
├── export_1.jpg .. 6.jpg   # 1080x1350 Instagram-ready
├── export_hd_1.jpg .. 6.jpg # 2160x2700 archive quality
```

---

## Key Learnings

1. **Never upscale.** Render at target resolution or use deviceScaleFactor.
2. **Clamp max values must match the canvas.** A 1080px canvas needs ~56px titles, not 34px.
3. **Inject CSS during export.** Never modify the original index.html — inject overrides via Playwright `page.evaluate()`.
4. **Crop 1px border artifact.** The `.ig-slide` border adds 1px to each dimension. Crop from center after screenshot.
5. **JPEG quality 100 for Instagram.** No visible compression artifacts at reasonable file sizes.
6. **Font sizes for 1080x1350 canvas:** Title ~52-56px, body ~28-30px, features ~22-28px, stats ~38-42px.
7. **Watermark avatar:** Scale up to 36px (from default 24px) for better visibility on the larger canvas.
