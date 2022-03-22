pinas
=====

Pinas is a library for evaluating Python expressions supplied as text from a
potentially untrusted source.

The expression is evaluated in a custom namespace, with many features not
available: There is no `open`, no `import`, no `def`, no `class`, in fact no
statements at all, other than expressions.  Library functions are available only to
the extent that they have been made explicitly available.

Sandboxing Python is `a`_ `difficult`_ `problem`_, everyone agrees.  Practially
insoluble.  And when you're done, you've left with functionality so decimated
that you're not really writing Python code at all, it's just a glorified
calculator.

And that's what pinas is, a glorified calculator.  With the ability to add
custom application-specific functions, in the form of a backing module.

The backing module
++++++++++++++++++

So what happens when the expressive power Python expressions falls short?  Well,
that's when the *backing module* comes into play.  A programmer will then need
to write the needed functionality, and place a function in a dedicated module,
which makes the new function available to use in expressions.

The backing module is a dictionary or dictionary-like object which contains an
``__all__`` key with a list of names to be made available to expressions.

How to use
++++++++++

Create an empty Python module with an ``__all__``:

.. code-block:: python
    __all__ = []

This is the backing module. Let's put something in that module: the square root function.

.. code-block:: python

    # backing_module.py
    __all__ = ['sqrt']
    from math import sqrt

Next, import it and create a `Backend` object:

.. code-block:: python

    import pinas
    import backing_module

    backend = pinas.Backend(module=backing_module)

Then compile the expression you wish to evaluate:

.. code-block: python
   expr = pinas.Expression("(-b + s * sqrt(b**2 - 4 * a * c)) / (2*a)", backend=backend)

This expression has 5 free variables.  a, b, c and s.  Their values need to
come from somewhere, so to evaluate the expression, provide them in a namespace:

.. code-block: python
   a,b,c,s = 1,-3,-4,1
   x = expr.eval(dict(a=a, b=b, c=c, s=s))
   print(x)


Alternate hard and soft layers
++++++++++++++++++++++++++++++

The idea is to have customisation at two levels: There's a soft layer of
user-configurable expressions, the expressions evaluated with this library. And
behind that is a hard layer of programming, providing capabilities to the users
in the form of predefined functions to use in expressions.

This showcases *the principle of alternate hard and soft layers*.  Decades back, this
principle was bandied about a lot in software engineering circles.  No one ever
explained what this principle meant, I think mostly because everyone was too
embarressed that they didn't already know it to ask.  I'm not sure I can explain
it either, but the expression/backing file division of labour is an example of it.

This is my answer to the problem presented in `the configuration complexity
clock`_: Suppose you represent your configuration as a stored set of pinas
expressions.  Then, at some point, you run into a problem where pinas
expressions are not powerful enough for what you need to do, or maybe they are
just excessively verbose.  Then, instead of going all *inner platform effect*
and improving the pinas expression evaluator to support more complicated
expressions, you just add a helper function to the backing module for the
particular problem at hand.


Why not to use pinas
++++++++++++++++++++

Because it isn't battle-hardened.

Because (paraphrasing Victor Stinner), the security of a sandbox is the security
of its weakest part. A single bug is enough to escape the whole sandbox.

Because I explicitly disawow any security guarantees.  I've done my best, but my
best might not be good enough.  I am myself not using pinas on any public-facing
web server; if you do, then you are responsible for any security disasters
arising from it.



The name
++++++++

*Pinas* stands for *"Pinas Is Not A Sandbox"*.


.. _a: https://stackoverflow.com/questions/3513292/python-make-eval-safe
.. _difficult: https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
.. _problem: https://lwn.net/Articles/574215/
.. _the configuration complexity clock: http://mikehadlow.blogspot.com/2012/05/configuration-complexity-clock.html
