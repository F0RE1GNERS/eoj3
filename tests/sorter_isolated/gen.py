from random import Random

INT_MAX = 2000000000

def solve(kase, arr):
    fi = ' '.join(map(str, sorted(arr, key = lambda x : str(x))))
    se = ' '.join(map(str, sorted(arr)))
    output(kase, str(len(arr)) + '\n' + ' '.join(map(str, arr)), fi + '\n' + se)


# Preparation
r = Random()


# Write Files
def output(kase, indata, outdata):
    input_file = open('data/sort%d.in' % kase, 'w')
    output_file = open('data/sort%d.ans' % kase, 'w')
    print(indata, file=input_file)
    print(outdata, file=output_file)
    input_file.close()
    output_file.close()


def generate(length, a, b):
    res = []
    for i in range(length):
        if r.randint(0, 1) == 0:
            res.append(int(pow(10, r.uniform(0, 6))))
        else:
            res.append(r.randint(a, b))
    return res


if __name__ == '__main__':
    solve(0, [10, 9, 8, 7, 5])
    solve(1, [100, 1001, 1002, 200, 10])
    solve(2, [0, 20, 200, 2000, 20000, 200000, 2000, 20, 0, 0, 0, INT_MAX ])
    solve(3, [500, 3000, 0, 0, -999, -8, 9, 1357924680, 9, -1, -3, -20 ])
    solve(4, [2147483647, -2147483648])
    solve(5, generate(5000, -INT_MAX, INT_MAX))
    solve(6, generate(10000, -INT_MAX, INT_MAX))
    for kase in range(7, 10):
        solve(kase, generate(100000, -INT_MAX, INT_MAX))
