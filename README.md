# RINA

python -m pytest test_hybrid.py
python -m pytest test_rina.py
python -m pytest test_tcp.py

python visualize_rina.py
python visualize_hybrid.py
python visualize_tcp.py
python visualize_compare.py