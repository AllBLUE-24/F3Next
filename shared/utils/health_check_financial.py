from agents.health_check.knowledge_base import KNOWLEDGE_BASE
from shared.constants.health_check_constants import OPTION_MAP 

def get_mapped_value(user_input, category):
    """
    Robust Fuzzy Matcher: Strips ALL spaces and symbols to match the map key.
    """
    if not user_input:
        return 10000000 if category == "turnover" else 1000000

    # Normalize: lowercase, remove spaces, remove symbols
    clean_input = str(user_input).lower().replace(" ", "").strip()
    
    # Direct Map Lookup
    if clean_input in OPTION_MAP:
        return OPTION_MAP[clean_input]
        
    # Regex Fallback
    clean_val = clean_input.replace(",", "").replace("₹", "").replace("lakhs", "").replace("cr", "")
    numbers = re.findall(r"[\d\.]+", clean_val)
    if numbers:
        val = float(numbers[0])
        if "cr" in clean_input: return val * 10000000
        if "lakh" in clean_input or "lac" in clean_input: return val * 100000
        return val
        
    return 10000000 if category == "turnover" else 1000000    # ... (the exact logic from your agent.py)