# shared/constants/health_check_constants.py

OPTION_MAP = {
    # Turnover Options
    "₹50l-₹2cr": 12500000,   # 1.25 Cr
    "₹2cr-₹10cr": 60000000,  # 6 Cr
    "₹10cr-₹50cr": 300000000, # 30 Cr
    "₹50cr+": 600000000,     # 60 Cr

    # Inventory Options
    "<₹10lakhs": 500000,      # 5 Lakhs
    "₹10lakhs-₹50lakhs": 3000000, # 30 Lakhs
    "₹50lakhs-₹2crores": 12500000, # 1.25 Cr
    "ihonestlydon'tknow(noliverecord)": -1, 
}