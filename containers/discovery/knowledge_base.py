KNOWLEDGE_BASE = {

  "validation_rules": {
    "scale_ratios": {
      "rule": "Revenue per employee usually falls between ₹5L - ₹5Cr.",
      "flag_if": "User claims ₹100 Cr turnover with 2 employees (Suspicious)."
    },
    "industry_keywords": {
      "manufacturing": ["make", "produce", "assemble", "fabricate", "factory", "plant"],
      "retail": ["sell", "shop", "distribute", "trade", "store", "outlet"],
      "service": ["consult", "repair", "maintain", "amc", "advisory"]
    },
    "gibberish_detection": {
      "min_length": 3,
      "reject_patterns": ["abc", "test", "stuff", "na", "no", "yes", "idk"]
    }
  },
  "clarification_strategies": {
    "vague_industry": "If user says 'We do business', ask: 'Could you specify if you manufacture products or trade them?'",
    "vague_scale": "If user says 'Big', ask: 'Could you share an approximate annual turnover range?'"
  }
  
}