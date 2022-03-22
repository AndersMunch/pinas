import sys, unittest, builtins
sys.path.insert(0, '../src')
import pinas

class module:
    __all__ = ['add','add_d','oct','bit_length','pos_only','implied','name_collision','implied_name_collision']
    @staticmethod
    def add(x,y):
        return x+y
    @staticmethod
    def add_d(x,*,d):
        return x+d
    @staticmethod
    def oct(x):
        return x=='octavian'
    @staticmethod
    def bit_length():
        return 42
    @staticmethod
    def pos_only(x,/,y,z,*,p=0):
        return x+y+z+p

    @staticmethod
    def implied(x,*,b):
        return (x,b)

    @staticmethod
    def implied_name_collision(a,*,b):
        return (a,b)

    @staticmethod
    def name_collision(a,b):
        return (a,b)

module = module()
backend = pinas.Backend(module=module)


class Test_Cond(unittest.TestCase):
    def _test_ex(self, expr_text, expected_value):
        expr = pinas.Expression(expr_text, backend)
        namespace = dict(
            a=0,
            b=1,
            c=2,
            d=3,
            )
        got_value = expr.eval(namespace)
        self.assertEqual(got_value, expected_value)

    def _raises_PinasExpressionError(self, expr):
        self.assertRaises(pinas.PinasExpressionError, lambda:pinas.Expression(expr, backend))

    def test_literals(self):
        self._test_ex("(2**4 - 10) / 2", 3)

    def test_2plus2(self):
        self._test_ex("c+c", 4)

    def test_funcall(self):
        self._test_ex("add(b, d)", 4)

    def test_implied_argument(self):
        self._test_ex("add_d(10)", 13)

    def test_override_builtins(self):
        self._test_ex("oct('octavian')", True)
        self._test_ex("oct('caesar')", False)

    def test_illegal_builtins(self):
        expr = pinas.Expression('open("helloworld.txt")', backend)
        self.assertRaises(pinas.PinasNameError, lambda:expr.eval(dict()))

    def test_illegal_as_attribute(self):
        self._raises_PinasExpressionError('1 . bit_length()')

    def test_function_not_attribute(self):
        expr = pinas.Expression('bit_length()==42', backend)
        self.assertTrue(expr.eval(dict()))

    def test_legal_named_attribute(self):
        self._test_ex("add(x=2, y=1)", 3)

    def test_unknown_named_att(self):
        self._raises_PinasExpressionError("add(add=2, y=1)")

    def test_mixed_args(self):
        self._test_ex("pos_only(1,2,3)", 6)

    def test_mixed_args_named(self):
        self._test_ex("pos_only(1,y=2,z=3,p=4)", 10)

    def test_pos_only_yet_named(self):
        self._raises_PinasExpressionError("pos_only(x=1,y=2,z=3,p=4)")

    def test_implied(self):
        self._test_ex("implied(x='x')", ('x', 1))

    def test_avoided_name_collision(self):
        self._test_ex("name_collision(1,2)", (1,2))

    def test_named_parameters_separate(self):
        self._test_ex("name_collision(a='a',b=a)", ('a',0))

    def test_named_parameters_separate_with_implied(self):
        self._test_ex("implied_name_collision(a='a')", ('a', 1))


class Test_ImpliedArguments(unittest.TestCase):
    def test_builtins_no_matches(self):
        # ImpliedArguments looks for a corner case that no normal function will match.
        # Verify against a conveniently easily accessible collection of objects.
        for k,v in vars(builtins).items():
            self.assertEqual(pinas.ImpliedArguments(v), (), k)

    # Test that functions with the weird property of having non-default keyword-only arguments don't
    # really exist, except for oddballs such as here and, for some reason, stdlib
    # warnings._add_filter.
    #
    # (Obviously this test will fail as soon a pinas.py starts seeing use, so disabled.)
    def _test_gc_all(self):
        import gc
        for obj in gc.get_objects():
            ia = pinas.ImpliedArguments(obj)
            if ia!=():
                if obj.__name__ not in ['_add_filter','add_d','implied','implied_name_collision']:
                    self.assertEqual(ia, (), obj.__name__)

    def test_pos_only(self):
        self.assertEqual(pinas.ImpliedArguments(module.pos_only), ())

    def test_implied(self):
        self.assertEqual(pinas.ImpliedArguments(module.implied_name_collision), ('b',))


class Test_NamedParameterNames(unittest.TestCase):
    def test_pos_only(self):
        self.assertEqual(pinas.NamedParameterNames(module.pos_only), ('y', 'z', 'p'))

    def test_none(self):
        self.assertEqual(pinas.NamedParameterNames(module.bit_length), ())

    def test_one(self):
        self.assertEqual(pinas.NamedParameterNames(module.oct), ('x',))


if __name__=='__main__':
    unittest.main()
