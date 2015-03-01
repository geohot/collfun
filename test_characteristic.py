from characteristic import Characteristic

def test_one_plus_one():
  assert str(Characteristic.add(Characteristic(1), Characteristic(1))) == "0"*30 + "10"


"""
x1 = Characteristic("0"*31 + "x")
x2 = Characteristic("0"*31 + "x")
xx = Characteristic.add(x1, x2)
for i in range(4):
  print xx.bits[i].prob

print "%s + %s = %s" % (x1, x2, xx)
"""

x1 = Characteristic("1"*32)
x2 = Characteristic("1"*32)
x3 = Characteristic("1"*32)
x4 = Characteristic("1"*32)
x5 = Characteristic("1"*32)
xx = Characteristic.add(x1, x2, x3, x4, x5)
print "%s + %s = %s" % (x1, x2, xx)

