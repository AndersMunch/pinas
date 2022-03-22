import functools, io, token, tokenize, builtins, itertools

# Whitelists.
# Select builtins and operator names that are always available.
# There are plenty of DOS opportunities here; e.g. removing pow would not fix that.
default_allow_builtin_names = set([
    'False', 'None', 'True', 'abs', 'all', 'any', 'bin', 'bytes', 'chr', 'float', 'hex', 'int', 'len',
    'max', 'min', 'oct', 'ord', 'pow', 'range', 'round', 'sorted', 'str', 'sum',
    ])

# Non-function identifiers that are allowed in expressions.
default_allow_keywords = set(['and', 'or', 'not', 'in', 'if', 'else', 'for'])
default_allow_methods = set([
    'encode', 'decode', 'from_hex', 'split', 'join', 'upper', 'lower', 'casefold', 'replace', 'find', 'format',
    'isalpha', 'isdigit', 'isascii', 'isdecimal', 'isdigit', 'isidentifier', 'islower', 'isupper', 'isnumeric',
    'isprintable', 'isspace', 'strip', 'lstrip', 'rstrip', 'startswith', 'endswith', 'rjust', 'ljust', 'zfill',
    'index'])

# Blacklist.
# In no way intrinsic to security, just an extra failsafe for someone providing a custom 'allow_builtin_names'.
known_unsafe_builtins = set([
    'getattr', 'setattr', 'delattr', 'vars', 'open', '__import__', 'compile', 'exec', 'eval', 'globals', 'locals',
    'memoryview', 'delattr', '__loader__', '__build_class__', 'property', 'staticmethod', 'classmethod', 'type',
    'object', 'super', 'vars', 'dir',
    ])


class PinasError(Exception): pass

class PinasNameError(PinasError):
    def __init__(self, names):
        self.names = names

    def __str__(self):
        if len(self.names)==1:
            return "No value for name '%s'" % (next(iter(self.names)),)
        else:
            return "No value for names: %s" % (', '.join(self.names),)

class PinasExpressionError(PinasError):
    def __init__(self, tok, errtext):
        self._tok = tok
        self._errtext = errtext

    def __str__(self):
        return 'Line %d:%d: %s' % (self._tok.start[0], self._tok.start[1], self._errtext)


def NamedParameterNames(fn):
    """!
    @brief Get names available to use as named parameters.
    """
    try:
        co = fn.__code__
    except AttributeError:
        return ()
    return co.co_varnames[co.co_posonlyargcount:co.co_argcount+co.co_kwonlyargcount]


def ImpliedArguments(fn):
    """!
    @brief Check for keyword-only arguments with no default value.
    """
    try:
        co = fn.__code__
    except AttributeError:
        return ()
    if co.co_kwonlyargcount == 0:
        return ()
    else:
        kwonlyargs = co.co_varnames[co.co_argcount:co.co_argcount+co.co_kwonlyargcount]
        if fn.__kwdefaults__ is None or not any(anavn in fn.__kwdefaults__ for anavn in kwonlyargs):
            return kwonlyargs
        else:
            return ()

def SupplyImpliedArguments(fn, namespace):
    """!
    @brief Supply values from namespace to keyword-only no-default arguments.
    @param[in] fn		A function.
    @param[in] namespace	A dict(str => ..)
    @return fn wrapped to get arguments from namespace.
    """
    iargs = ImpliedArguments(fn)
    if len(iargs)==0:
        return fn
    else:
        @functools.wraps(fn)
        def supply_namespace_args(*args, **kwargs):
            try:
                full_kwargs = { iarg:namespace[iarg] for iarg in iargs }
            except KeyError:
                raise PinasNameError([iarg for iarg in iargs if not iarg in namespace])
            full_kwargs.update(kwargs)
            return fn(*args, **full_kwargs)
        return supply_namespace_args


class Backend:
    """!
    @brief The context for expression evaluation.
    """
    def __init__(self,
                 module,
                 allow_builtin_names=None,
                 allow_keywords=None,
                 allow_methods=None,
                 ):
        """!
        @param[in] module	A module. module.__all__ is a list of functions available to expressions.
        @param[in] allow_*	Optionally, override which builtins and methods names are considered safe.
        """
        if allow_builtin_names is None:
            allow_builtin_names = default_allow_builtin_names
        if len(allow_builtin_names & known_unsafe_builtins) != 0:
            raise ValueError
        allow_builtin_functions = dict((n, getattr(builtins,n)) for n in allow_builtin_names)
        if allow_keywords is None:
            allow_keywords = default_allow_keywords
        if allow_methods is None:
            allow_methods = default_allow_methods

        self._allow_methods = allow_methods
        self._allow_keywords = allow_keywords
        self._allow_keywords_and_methods = allow_keywords | allow_methods
        self.predefined_names = set(module.__all__) | allow_builtin_names
        self._module_functions = dict((n,getattr(module,n)) for n in module.__all__)
        self._SupplyImpliedArguments_for = [(n,fn)
                                            for n,fn in self._module_functions.items()
                                            if len(ImpliedArguments(fn)) > 0]
        self.predefined_functions = dict(self._module_functions)
        for k,v in allow_builtin_functions.items():
            if k not in self._module_functions:
                self.predefined_functions[k] = v

        self._named_parameter_names_for = dict()
        for n,fn in itertools.chain(allow_builtin_functions.items(), self._module_functions.items()):
            # Disallow named parameters that start with '_'.  Technically no need to do that, but
            # there probably was a reason for the underscore,
            allowed_named_params = set(n for n in NamedParameterNames(fn) if not n.startswith('_'))
            self._named_parameter_names_for[n] = allowed_named_params - set(ImpliedArguments(fn))


class Expression:
    def __init__(self, expr, backend):
        """!
        @brief A Python expression.
        @param[in] expr		A str with the text of the expression.
        @param[in] backend	A Backend in which to evaluate it.
        @par
        If a syntax error in expr is detected then an PinasExpressionError is raised, but it
        might not the detected until .eval time.
        """
        self._backend = backend

        # Extract identifiers from the expression.
        # Also, remove newlines, so that the expression may span multiple lines without parentheses.
        unbound_names = set()
        used_named_params = set()
        available_named_parameter_names = set()
        net_expr = []
        net_toks = []
        prev_end = (1, 0)
        prev = None
        for tok in tokenize.generate_tokens(io.StringIO(expr).readline):
            if tok.start != prev_end:
                if tok.start[0]==prev_end[0]:
                    net_expr.append(' '*(tok.start[1]-prev_end[1]))
                else:
                    net_expr.append('  ')
            if tok.type==token.NAME:
                if prev is not None and prev.string=='.':
                    if tok.string not in self._backend._allow_methods:
                        raise PinasExpressionError(tok, 'Illegal method .%s' % (tok.string,))
                else:
                    available_named_parameter_names.update(backend._named_parameter_names_for.get(tok.string, ()))
                    unbound_names.add(tok.string)
            elif tok.type==token.ERRORTOKEN:
                raise PinasExpressionError(tok, 'Syntax error')
            elif tok.type==token.OP and tok.string[-1]=='=':
                if tok.string=='=':
                    if prev is not None and prev.type==token.NAME:
                        if prev.string not in available_named_parameter_names:
                            raise PinasExpressionError(tok, 'No such named parameter: %s' % (prev.string,))
                        used_named_params.add(prev.string)

                    else:
                        raise PinasExpressionError(tok, 'Syntax error')
                elif tok.string not in ['=','==','!=','<=','>=']:
                    # Assignments are banned, but only ':=' is really needed, because other versions are
                    # not legal in expressions, only statements.
                    # '=' is needed for named parameters.
                    raise PinasExpressionError(tok, 'Illegal operator %s' % (tok.string,))
            if tok.type in [token.COMMENT, token.NEWLINE, token.INDENT, token.DEDENT, token.ENDMARKER, token.NL]:
                pass
            else:
                net_toks.append(tok)
                net_expr.append(tok.string)
                prev_end = tok.end
                prev = tok

        self.expr = ''.join(net_expr).strip()
        self._net_tokens = net_toks

        self.predefined_names = (unbound_names & backend.predefined_names) - backend._allow_keywords_and_methods
        self.free_variables = unbound_names - backend.predefined_names - backend._allow_keywords_and_methods

        for n,fn in backend._SupplyImpliedArguments_for:
            if n in self.predefined_names:
                for implied_arg in ImpliedArguments(fn):
                    if implied_arg in backend.predefined_names:
                        self.predefined_names.add(implied_arg)
                    else:
                        self.free_variables.add(implied_arg)

        self._base_namespace = dict(__builtins__=dict())
        for n in self.predefined_names:
            self._base_namespace[n] = backend.predefined_functions[n]



    def net_tokens(self):
        """!
        @return The expression as Python tokens, excluding whitespace and comments.
        """
        return self._net_tokens

    def effective_namespace(self, namespace):
        """!
        @param[in] namespace	A dict(str => ...) with values for free variables.
        @return A dict(str => ...) with the globals() environment for eval'ing the expression.
        """
        eff_namespace = self._base_namespace.copy()
        for n in self.free_variables:
            if n in eff_namespace:
                raise ValueError("'%s' is ambiguous" % (n,))
            try:
                eff_namespace[n] = namespace[n]
            except KeyError:
                pass
        for n,fn in self._backend._SupplyImpliedArguments_for:
            if n in eff_namespace:
                eff_namespace[n] = SupplyImpliedArguments(fn, eff_namespace)
        return eff_namespace

    def eval(self, namespace):
        """!
        @brief Compute the value of the expression.
        @param[in] namespace	dict(str => value) with values for free variables.
        @return The computed value.
        An PinasNameError exception arises if any free variables are unsatisfied.
        """
        eff_namespace = self.effective_namespace(namespace)
        try:
            return eval(self.expr, eff_namespace)
        except NameError as exc:
            missing = set(ident for ident in self.free_variables if ident not in namespace)
            if getattr(exc, 'name', None) in missing:
                # If the expression contains code like "foo if baz else bar", then 'missing' may
                # contain additional names that are not actually needed.  But in the typical case,
                # listing all unbound identifiers is more helpful.
                raise PinasNameError(missing)
            raise
