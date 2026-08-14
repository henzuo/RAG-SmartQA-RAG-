from pathlib import Path

# 1. 原始 __file__
print("="*50)
print(f"1. __file__ = {__file__}")
p1 = Path(__file__)
print(f"2. Path(__file__) = {p1}")
print(f"   类型：{type(p1)}")

# 不带resolve
p_no_resolve = Path(__file__).parent
print(f"\n3. Path(__file__).parent【无resolve】 = {p_no_resolve}")

# 带上resolve
p_resolve = Path(__file__).resolve()
print(f"\n4. Path(__file__).resolve() = {p_resolve}")
p_base = Path(__file__).resolve().parent
print(f"5. .resolve().parent = {p_base}")

# 判断是不是绝对路径
print(f"\n6. Path(__file__).is_absolute() → {Path(__file__).is_absolute()}")
print(f"7. resolve之后.is_absolute() → {p_resolve.is_absolute()}")