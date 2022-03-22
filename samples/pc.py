# A simple calculator.
import sys
sys.path.insert(0, '../src')
import argparse
import pinas
import pc_backing

backend = pinas.Backend(pc_backing)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('expression', nargs='?', action='store')
    args = ap.parse_args()

    expr_text = args.expression

    while 1:
        if expr_text is None:
            expr_text = input('Compute: ')
            if expr_text == '':
                break

        try:
            expr = pinas.Expression(expr_text, backend)
            val = expr.eval(dict())
        except Exception as exc:
            print('Error:', str(exc))
        else:
            print(val)

        if args.expression is not None:
            break
        else:
            expr_text = None


if __name__=='__main__':
    main()
