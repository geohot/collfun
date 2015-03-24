dv = expand([0,0,0,0,0x80000000,0,0,0,0,0,0x80000000,0,0x80000000,0,0,0], 43)
diff = dv_to_differential(dv)

for i in range(len(diff)):
  print "%3d %s" % (i, bprint(diff[i]))

exit(0)


w = tonum("hello\x80" + "\x00"*(56 - 6) + struct.pack("!Q", 8*5))
print w
print tonum("67452301efcdab8998badcfe10325476c3d2e1f0".decode("hex"))

print map(hex, expand(w))
print map(hex, sha1(expand(w)))

exit(0)

#print len(dv)




m1 = tonum("bc 7e 39 3a 04 70 f6 84 e0 a4 84 de a5 56 87 5a cd df f9 c8 2d 02 01 6b 86 0e e7 f9 11 e1 84 18 71 bf bf f1 06 70 95 c9 ed 44 af ee 78 12 24 09 a3 b2 eb 2e 16 c0 cf c2 06 c5 20 28 10 38 3c 2b 73 e6 e2 c8 43 7f b1 3e 4e 4d 5d b6 e3 83 e0 1d 7b ea 24 2c 2b b6 30 54 68 45 b1 43 0c 21 94 ab fb 52 36 be 2b c9 1e 19 1d 11 bf 8f 66 5e f9 ab 9f 8f e3 6a 40 2c bf 39 d7 7c 1f b4 3c b0 08 72".replace(" ", "").decode("hex"))
m2 = tonum("bc 7e 39 3a 04 70 f6 84 e0 a4 84 de a5 56 87 5a cd df f9 c8 2d 02 01 6b 86 0e e7 f9 11 e1 84 18 71 bf bf f1 06 70 95 c9 ed 44 af ee 78 12 24 09 a3 b2 eb 2e 16 c0 cf c2 06 c5 20 28 10 38 3c 2b 7f e6 e2 ca 83 7f b1 2e fa 4d 5d aa df 83 e0 19 c7 ea 24 36 0b b6 30 44 4c 45 b1 5f e0 21 94 bf f7 52 36 bc eb c9 1e 09 a9 11 bf 93 4a 5e f9 af 23 8f e3 72 f0 2c bf 29 d7 7c 1f b8 84 b0 08 62".replace(" ", "").decode("hex"))

#q = sha1(expand(w))
#print m1[0:16] == m2[0:16]

mm1 = sha1(expand(m1[16:32]))
mm2 = sha1(expand(m2[16:32]))
#w = xor(expand(m1[16:32]), expand(m2[16:32]))
a = xor(mm1, mm2)

#print mm1
#print mm2

#dump32(xor(mm1, mm2))

for i in range(-5, 80):
  print "%3d %32s %32s" % (i,
    Characteristic(a[i+5]),
    Characteristic(diff[i]) if i >= 0 else "",
    )
    #Characteristic(dv[i]) if i >= 0 else "",
    #bprint(w[i]) if i >= 0 else "",





"""
dump32(w)
print "Q"
dump32(q)

out = []
for i in range(0, 5):
  rotate = 0 if i < 2 else 30
  out.append((rl(q[4-i], rotate) + rl(q[-1-i], rotate)) & 0xFFFFFFFF)

print map(hex, out)
"""



