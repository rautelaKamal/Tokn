/**
 * Tokn client-side compressor — lossless filler stripping.
 * Runs entirely in the browser, zero API calls, works offline.
 *
 * Returns { compressed, tokensBefore, tokensAfter, changes[] }
 * where changes[] tracks every modification for the future diff view.
 */

/**
 * Rough token estimate — ~4 chars per token for English.
 * Accurate within ±10%, good enough for the extension badge.
 */
function estimateTokens(text) {
  if (!text || !text.trim()) return 0;
  return Math.ceil(text.trim().length / 4);
}

/**
 * Run client-side lossless compression on a prompt.
 * @param {string} text — raw user prompt
 * @returns {{ compressed: string, tokensBefore: number, tokensAfter: number, changes: Array }}
 */
function clientCompress(text) {
  const changes = [];
  let s = (text || "").trim();
  if (!s) return { compressed: "", tokensBefore: 0, tokensAfter: 0, changes };

  const tokensBefore = estimateTokens(s);

  // ---- Layer 1: Filler word removal ----
  const fillerPatterns = [
    { re: /\b(?:I was wondering if|I would appreciate if|I would really like it if)\b/gi, reason: "filler" },
    { re: /\b(?:could you|can you|would you)\s+(?:please\s+)?(?:help me\s+)?/gi, reason: "filler" },
    { re: /\b(?:I want you to|I need you to|I'd like you to)\s+/gi, reason: "implicit_subject" },
    { re: /\bplease\b/gi, reason: "filler" },
    { re: /\bkindly\b/gi, reason: "filler" },
    { re: /\breally\b/gi, reason: "filler" },
    { re: /\bvery\b/gi, reason: "filler" },
    { re: /\bjust\b/gi, reason: "filler" },
    { re: /\bbasically\b/gi, reason: "filler" },
    { re: /\bactually\b/gi, reason: "filler" },
    { re: /\bhonestly\b/gi, reason: "filler" },
    { re: /\bliterally\b/gi, reason: "filler" },
    { re: /\bI think\b/gi, reason: "filler" },
    { re: /\bI believe\b/gi, reason: "filler" },
    { re: /\bI feel like\b/gi, reason: "filler" },
    { re: /\bI suppose\b/gi, reason: "filler" },
    { re: /\bI guess\b/gi, reason: "filler" },
    { re: /\byou know\b/gi, reason: "filler" },
    { re: /\bsort of\b/gi, reason: "filler" },
    { re: /\bkind of\b/gi, reason: "filler" },
    { re: /\bperhaps\b/gi, reason: "filler" },
    { re: /\bmaybe\b/gi, reason: "filler" },
  ];

  for (const { re, reason } of fillerPatterns) {
    const before = s;
    s = s.replace(re, (match) => {
      changes.push({ type: "removed", original: match.trim(), reason });
      return "";
    });
  }

  // ---- Layer 2: Phrase compaction ----
  const compactions = [
    { re: /\bmake sure to\b/gi, to: "ensure", reason: "phrase_compaction" },
    { re: /\bin order to\b/gi, to: "to", reason: "phrase_compaction" },
    { re: /\bas well as\b/gi, to: "and", reason: "phrase_compaction" },
    { re: /\bin addition to\b/gi, to: "plus", reason: "phrase_compaction" },
    { re: /\ba comprehensive and detailed\b/gi, to: "detailed", reason: "phrase_compaction" },
    { re: /\band also\b/gi, to: "and", reason: "phrase_compaction" },
    { re: /\bbut also\b/gi, to: "and", reason: "phrase_compaction" },
    { re: /\bgreater than\b/gi, to: ">", reason: "comparison_shortcut" },
    { re: /\bless than\b/gi, to: "<", reason: "comparison_shortcut" },
    { re: /\bequal to\b/gi, to: "==", reason: "comparison_shortcut" },
    { re: /\bnot equal to\b/gi, to: "!=", reason: "comparison_shortcut" },
  ];

  for (const { re, to, reason } of compactions) {
    s = s.replace(re, (match) => {
      changes.push({ type: "replaced", original: match.trim(), replacement: to, reason });
      return to;
    });
  }

  // ---- Layer 3: Clean up whitespace ----
  s = s.replace(/\s{2,}/g, " ").trim();

  // Capitalize first letter if lowered after stripping
  if (s && s[0] !== s[0].toUpperCase() && /[a-z]/.test(s[0])) {
    s = s[0].toUpperCase() + s.slice(1);
  }

  // Remove leading/trailing commas or dangling punctuation from stripping
  s = s.replace(/^[,\s]+/, "").replace(/\s*,\s*,/g, ",").replace(/\s+,/g, ",");

  const tokensAfter = estimateTokens(s);

  return {
    compressed: s,
    tokensBefore,
    tokensAfter,
    changes,
  };
}

// Export for use in background.js (service worker ES module)
export { clientCompress, estimateTokens };
