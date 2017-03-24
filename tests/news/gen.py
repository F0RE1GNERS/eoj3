from random import randint

def get_random_list(length, maxv):
    lst = []
    for i in range(length):
        lst.append(randint(-maxv, maxv))
    return lst

n = [5, 10, 15, 100, 1000, 10000, 200000, 200000, 200000, 200000]
v = [10, 10, 10, 1000, 1000, 1000, 10000, 30000, 50000, 100000]

for i in range(10):
    fin = open('data/news%d.in' % i, 'w')
    fout = open('data/news%d.out' % i, 'w')
    a = get_random_list(n[i], v[i])
    b = get_random_list(n[i], v[i])
    print(len(a), file=fin)
    print(' '.join(map(str, a)), file=fin)
    print(' '.join(map(str, b)), file=fin)
    la = sorted(a)
    lb = sorted(b, reverse=True)
    ans = 0
    for i in range(len(a)):
        ans += (la[i] + lb[i]) ** 2
    print(ans, file=fout)
    fin.close()
    fout.close()
