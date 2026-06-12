"""Browser-side evaluation scripts for Playwright export preflight."""

GEOMETRY_EVAL_SCRIPT = """
(params) => {
  const {
    selectors,
    footerGap,
    tolerance,
    nearLimit,
    slidesMeta,
  } = params;

  const violations = [];
  const warnings = [];
  const slideReports = [];

  const slideRoots = document.querySelectorAll(selectors.slide_root);
  if (slideRoots.length === 0) {
    return { skipped: true, violations, warnings, slideReports };
  }

  const getRect = (el) => {
    const r = el.getBoundingClientRect();
    return {
      top: r.top,
      left: r.left,
      bottom: r.bottom,
      right: r.right,
      width: r.width,
      height: r.height,
    };
  };

  const rectContains = (outer, inner, tol) =>
    inner.top >= outer.top - tol
    && inner.left >= outer.left - tol
    && inner.bottom <= outer.bottom + tol
    && inner.right <= outer.right + tol;

  const isVisible = (el) => {
    const style = window.getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') {
      return false;
    }
    const opacity = Number.parseFloat(style.opacity || '1');
    if (Number.isFinite(opacity) && opacity <= 0) {
      return false;
    }
    const rect = el.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  };

  const pushNearLimit = (items, slideNumber, code, message) => {
    items.push({
      code,
      slide_number: slideNumber,
      message,
      blocking: false,
    });
  };

  const pushBlocking = (items, slideNumber, code, message) => {
    items.push({
      code,
      slide_number: slideNumber,
      message,
      blocking: true,
    });
  };

  const checkOverflowStyle = (el, slideNumber, items) => {
    const style = window.getComputedStyle(el);
    const axes = ['overflowX', 'overflowY'];
    for (const axis of axes) {
      const value = style[axis];
      if (value === 'auto' || value === 'scroll') {
        pushBlocking(
          items,
          slideNumber,
          'layout_overflow_scroll',
          `${axis} must not be scrollable on static slides`,
        );
      }
    }
  };

  const checkCopyDescendants = (copyEl, presentationRect, slideNumber, items) => {
    const descendants = copyEl.querySelectorAll('*');
    for (const node of descendants) {
      if (!isVisible(node)) {
        continue;
      }
      const rect = getRect(node);
      if (!rectContains(presentationRect, rect, tolerance)) {
        pushBlocking(
          items,
          slideNumber,
          'layout_copy_descendant_overflow',
          'Visible copy descendant exceeds presentation bounds',
        );
        return;
      }
    }
  };

  for (const slideEl of slideRoots) {
    const slideNumber = Number.parseInt(
      slideEl.getAttribute('data-slide-number') || '0',
      10,
    );
    const meta = slidesMeta.find((entry) => entry.slideNumber === slideNumber);
    if (!meta) {
      continue;
    }

    const slideRect = getRect(slideEl);
    const slideViolations = [];
    const slideWarnings = [];

    checkOverflowStyle(slideEl, slideNumber, slideViolations);

    if (meta.isCta) {
      const card = slideEl.querySelector(selectors.cta_card);
      if (!card) {
        pushBlocking(
          slideViolations,
          slideNumber,
          'layout_missing_region',
          'CTA creator card is missing',
        );
      } else {
        checkOverflowStyle(card, slideNumber, slideViolations);
        const cardRect = getRect(card);
        if (!rectContains(slideRect, cardRect, tolerance)) {
          pushBlocking(
            slideViolations,
            slideNumber,
            'cta_card_out_of_bounds',
            'Creator card exceeds slide safe rectangle',
          );
        }
        if (meta.website) {
          const visibleText = card.innerText || '';
          const matches = visibleText.split(meta.website).length - 1;
          if (matches !== 1) {
            pushBlocking(
              slideViolations,
              slideNumber,
              'cta_website_count_invalid',
              `Configured website must appear exactly once (found ${matches})`,
            );
          }
        }
      }

      slideReports.push({
        slide_number: slideNumber,
        slide_type: meta.slideType,
        passed: slideViolations.length === 0,
        violations: slideViolations,
        warnings: slideWarnings,
      });
      violations.push(...slideViolations);
      warnings.push(...slideWarnings);
      continue;
    }

    const presentation = slideEl.querySelector(selectors.presentation);
    const copy = slideEl.querySelector(selectors.copy);
    const footer = slideEl.querySelector(selectors.footer);

    if (!presentation || !copy || !footer) {
      pushBlocking(
        slideViolations,
        slideNumber,
        'layout_missing_region',
        'Lower-third presentation regions are missing',
      );
      slideReports.push({
        slide_number: slideNumber,
        slide_type: meta.slideType,
        passed: false,
        violations: slideViolations,
        warnings: slideWarnings,
      });
      violations.push(...slideViolations);
      continue;
    }

    checkOverflowStyle(presentation, slideNumber, slideViolations);
    checkOverflowStyle(copy, slideNumber, slideViolations);

    const presentationRect = getRect(presentation);
    const footerRect = getRect(footer);

    const minTop = slideRect.top + slideRect.height * meta.copyStartRatio - tolerance;
    if (presentationRect.top < minTop) {
      pushBlocking(
        slideViolations,
        slideNumber,
        'layout_copy_above_boundary',
        'Presentation region starts above artwork-safe boundary',
      );
    } else if (presentationRect.top < minTop + nearLimit) {
      pushNearLimit(
        slideWarnings,
        slideNumber,
        'layout_near_limit',
        'Presentation region is near artwork-safe boundary',
      );
    }

    const maxBottom = footerRect.top - footerGap + tolerance;
    if (presentationRect.bottom > maxBottom) {
      pushBlocking(
        slideViolations,
        slideNumber,
        'layout_presentation_below_footer',
        'Presentation region overlaps footer gap',
      );
    } else if (presentationRect.bottom > maxBottom - nearLimit) {
      pushNearLimit(
        slideWarnings,
        slideNumber,
        'layout_near_limit',
        'Presentation region is near footer gap boundary',
      );
    }

    if (copy.scrollHeight > copy.clientHeight + tolerance) {
      pushBlocking(
        slideViolations,
        slideNumber,
        'layout_copy_overflow',
        'Copy content exceeds client height',
      );
    } else if (copy.scrollHeight > copy.clientHeight + tolerance - nearLimit) {
      pushNearLimit(
        slideWarnings,
        slideNumber,
        'layout_near_limit',
        'Copy content is near vertical overflow',
      );
    }

    if (copy.scrollWidth > copy.clientWidth + tolerance) {
      pushBlocking(
        slideViolations,
        slideNumber,
        'layout_copy_overflow',
        'Copy content exceeds client width',
      );
    }

    if (!rectContains(slideRect, footerRect, tolerance)) {
      pushBlocking(
        slideViolations,
        slideNumber,
        'layout_footer_out_of_bounds',
        'Footer exceeds slide bounds',
      );
    }

    checkCopyDescendants(copy, presentationRect, slideNumber, slideViolations);

    slideReports.push({
      slide_number: slideNumber,
      slide_type: meta.slideType,
      passed: slideViolations.length === 0,
      violations: slideViolations,
      warnings: slideWarnings,
    });
    violations.push(...slideViolations);
    warnings.push(...slideWarnings);
  }

  return { skipped: false, violations, warnings, slideReports };
}
"""

IMAGE_DECODE_SCRIPT = """
async (params) => {
  const {
    artworkSelector,
    avatarSelector,
    timeoutPer,
    timeoutTotal,
  } = params;

  const images = new Set();
  const collect = (selector) => {
    if (!selector) {
      return;
    }
    document.querySelectorAll(selector).forEach((node) => {
      if (node.tagName === 'IMG') {
        images.add(node);
        return;
      }
      node.querySelectorAll('img').forEach((img) => images.add(img));
    });
  };

  collect(artworkSelector);
  collect(avatarSelector);

  const reports = [];
  const deadline = Date.now() + timeoutTotal;

  for (const img of images) {
    const remaining = deadline - Date.now();
    if (remaining <= 0) {
      reports.push({
        src: img.currentSrc || img.src,
        slide_number: null,
        decoded: false,
        natural_width: img.naturalWidth || 0,
        natural_height: img.naturalHeight || 0,
        error_code: 'image_decode_timeout',
      });
      continue;
    }

    const perImageTimeout = Math.min(timeoutPer, remaining);
    try {
      await Promise.race([
        img.decode(),
        new Promise((_, reject) => {
          setTimeout(() => reject(new Error('timeout')), perImageTimeout);
        }),
      ]);
    } catch (_error) {
      reports.push({
        src: img.currentSrc || img.src,
        slide_number: null,
        decoded: false,
        natural_width: img.naturalWidth || 0,
        natural_height: img.naturalHeight || 0,
        error_code: 'image_decode_timeout',
      });
      continue;
    }

    const decoded = img.complete && img.naturalWidth > 0 && img.naturalHeight > 0;
    reports.push({
      src: img.currentSrc || img.src,
      slide_number: null,
      decoded,
      natural_width: img.naturalWidth || 0,
      natural_height: img.naturalHeight || 0,
      error_code: decoded ? null : 'image_decode_failed',
    });
  }

  return reports;
}
"""

FONT_CHECK_SCRIPT = """
async (params) => {
  const { fontSpecs, timeoutMs } = params;
  const deadline = Date.now() + timeoutMs;
  await Promise.race([
    document.fonts.ready,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error('font_ready_timeout')), timeoutMs);
    }),
  ]);

  const checks = [];
  for (const spec of fontSpecs) {
    if (Date.now() > deadline) {
      checks.push({
        family: spec.label,
        available: false,
        error_code: 'font_ready_timeout',
      });
      continue;
    }
    const available = document.fonts.check(spec.cssText);
    checks.push({
      family: spec.label,
      available,
      error_code: available ? null : 'font_unavailable',
    });
  }
  return checks;
}
"""
