from typing import Literal

from rdflib import Variable, URIRef

from search.rdf.namespace.xpath_functions import year_from_date, month_from_date, day_from_date

# list of supported aggregate functions
AGGREGATE_FUNCTION_LIST = ["SUM", "AVG", "COUNT", "SET", "MIN", "MAX", "SAMPLE"]
# list of supported functions expressions
FUNCTION_EXPRESSION_SUPPORTED_LIST = [
    "ASC",
    "DESC",
    "IRI",
    "ISBLANK",
    "ISLITERAL",
    "ISIRI",
    "ISNUMERIC",
    "BNODE",
    "ABS",
    "IF",
    "RAND",
    "UUID",
    "STRUUID",
    "MD5",
    "SHA1",
    "SHA256",
    "SHA384",
    "SHA512",
    "COALESCE",
    "CEIL",
    "FLOOR",
    "ROUND",
    "REGEX",
    "REPLACE",
    "STRDT",
    "STRLANG",
    "CONCAT",
    "STRSTARTS",
    "STRENDS",
    "STRBEFORE",
    "STRAFTER",
    "CONTAINS",
    "ENCODE_FOR_URI",
    "SUBSTR",
    "STRLEN",
    "STR",
    "LCASE",
    "LANGMATCHES",
    "NOW",
    "YEAR",
    "MONTH",
    "DAY",
    "HOURS",
    "MINUTES",
    "SECONDS",
    "TIMEZONE",
    "TZ",
    "UCASE",
    "LANG",
    "DATATYPE",
    "SAMETERM",
    "BOUND",
    "EXISTS",
]
XPATH_FUNCTIONS = [
    year_from_date,
    month_from_date,
    day_from_date,
]


def is_variable_supported(variable):
    """
    Function to check the input variable in query.
    The variable should have a n3() function that provides the n triple format output.

    :param variable: individual to be checked.
    :return: boolean
    """
    return hasattr(variable, "n3")


class STATEMENT(tuple):
    """
    Class to store a single triple in format of tuples.

    This object is used to define a n3() function for triples
    given as input in form of tuples. It extends tuple class and
    the objects can be accessed in a similar manner.

    Each triple has to be a tuple of length 3, in format (s, p, o).

    Made to be used internally and not be called by user.
    """

    def __new__(cls, statement):
        """
        Function to define the new object created using STATEMENT class.
        There should be 3 variables in the statement and all should be supported.

        :param statement: the variable to be converted to the given class.
        :return: tuple type STATEMENT
        """
        # has to be of length 3 (s, p, o)
        if len(statement) == 3:
            s, p, o = statement
            # check the variable support
            if is_variable_supported(s) and is_variable_supported(p) and is_variable_supported(o):
                return tuple.__new__(STATEMENT, (s, p, o))
            else:
                raise Exception(
                    "Values in the statement {} are not of acceptable types.".format(statement)
                )
        else:
            raise Exception("Statement has to be a tuple in the format (s, p, o)")

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is: "?s ?p ?o ."

        :return: string
        """
        return self[0].n3() + " " + self[1].n3() + " " + self[2].n3() + " ."


class Operators(object):
    """
    Class is meant to be used with FILTER while making a conditional query.

    To be used as:
    >> Operators.GT(var1, var2)
    The above statement gives an output of var1 > var2.

    This class can be nested inside itself to produce a complex expression.
    """

    @staticmethod
    def GT(left, right):
        """
        Greater than operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, ">", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def LT(left, right):
        """
        Less than operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, "<", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def EQ(left, right):
        """
        Equality operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, "=", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def NE(left, right):
        """
        Unequality operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, "!=", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def GE(left, right):
        """
        Greater than and equal to operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, ">=", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def LE(left, right):
        """
        Less than and equal to operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, "<=", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def AND(left, right):
        """
        And operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, "&&", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def OR(left, right):
        """
        Or operator. Accepts only 2 arguments.

        :param left: left argument for the operator
        :param right: right argument for the operator
        :return: CONDITIONAL_STATEMENT, storing the details.
        """
        # check the variables support in both arguments
        if is_variable_supported(left) and is_variable_supported(right):
            return CONDITIONAL_STATEMENT(left, "||", right)
        else:
            raise Exception("Operands are not of acceptable type.")

    @staticmethod
    def IN(left, *args, state: bool = True):
        """
        IN operator. Accepts the compulsory left argument and multiple right arguments.

        The IN operator can have multiple values for comparison.

        :param left: left argument for the operator
        :param args: multiple right arguments for the operator
        :param state: switch between "IN" and "NOT IN"
        :return: CONDITIONAL_STATEMENT, storing the details
        """
        # check the variables support in left argument
        if not is_variable_supported(left):
            raise Exception("Operands are not of acceptable type.")
        for var in args:
            if not is_variable_supported(var):
                raise Exception("Operands are not of acceptable type.")

        return CONDITIONAL_STATEMENT(left, "IN", *args, state=state)


class GROUP(STATEMENT):
    """
    Class to be used by the user, to input group graph patterns in the query.
    Usage as follows
    >> GROUP ( (s, p, o) )
    Output: { ?s ?p ?o . } .
    """

    def __new__(cls, *args):
        """
        Function to create the GROUP object.
        The input is converted to the super class object and stored as a tuple.

        :param args: statements to be used as group graph pattern
        :return: GROUP tuple object
        """
        statements = []
        for stmt in args:
            # convert the statements to supported format if not already present
            if not is_variable_supported(stmt):
                statements.append(STATEMENT(stmt))
            else:
                statements.append(stmt)

        return tuple.__new__(GROUP, statements)

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is:
        {
            stmt1 .
            stmt2 .
        }

        :return: string
        """
        n3_string = "{ \n"
        n3_string += " \n".join(map(lambda v: v.n3(), self))
        n3_string += "\n}"
        return n3_string


class UNION(STATEMENT):
    """
    Class to be used by the user, to input Alternative tuples in the query.
    Usage as follows
    >> UNION ( (s, p, o) )
    Output: UNION { ?s ?p ?o . } .
    """

    def __new__(cls, *args):
        """
        Function to create the UNION object.
        The input is converted to the super class object and stored as a tuple.

        :param args: statements to be used as graph pattern inside the UNION
        :return: UNION tuple object
        """
        statements = []
        for stmt in args:
            # convert the statements to supported format if not already present
            if not is_variable_supported(stmt):
                statements.append(STATEMENT(stmt))
            else:
                statements.append(stmt)

        return tuple.__new__(UNION, statements)

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is:
        UNION {
            stmt1 .
            stmt2 .
        }

        :return: string
        """
        n3_string = "UNION { \n"
        n3_string += " \n".join(map(lambda v: v.n3(), self))
        n3_string += "\n}"
        return n3_string


class OPTIONAL(STATEMENT):
    """
    Class to be used by the user, to input Optional tuples in the query.
    Usage as follows
    >> OPTIONAL ( (s, p, o) )
    Output: OPTIONAL { ?s ?p ?o . } .

    The optional conditional is also a statement, which can be used anywhere
    in the query. Thus, the STATEMENT class is extended for this purpose.
    """

    def __new__(cls, *args):
        """
        Function to create the OPTIONAL object.
        The input is converted to the super class object and stored as a tuple.

        :param args: statements to be used as graph pattern inside the OPTIONAL
        :return: OPTIONAL tuple object
        """
        statements = []
        for stmt in args:
            # convert the statements to supported format if not already present
            if not is_variable_supported(stmt):
                statements.append(STATEMENT(stmt))
            else:
                statements.append(stmt)

        return tuple.__new__(OPTIONAL, statements)

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is:
        OPTIONAL {
            stmt1 .
            stmt2 .
        } .

        :return: string
        """
        n3_string = "OPTIONAL { \n"
        n3_string += " \n".join(map(lambda v: v.n3(), self))
        n3_string += "\n} ."
        return n3_string


class VALUES(STATEMENT):
    """
    Class to be used by the user, to input VALUES in the query.
    Usage as follows
    >> VALUES ([Variable("v1"), Variable("v2")], [(Literal("1st value for ?v1"), Literal("1st value for ?v2")),
       (Literal("2nd value for ?v1"), Literal("2nd value for ?v2"))] )
    Output: VALUES (?v1, ?v2) { ("1st value for ?v1" "1st value for ?v2") ("2nd value for ?v1" "2nd value for ?v2") } .

    VALUES is also a statement, which can be used anywhere in the
    query. Thus, the STATEMENT class is extended for this purpose.
    """

    def __new__(cls, variables, values):
        """
        Function to create the VALUES object.
        The input is converted to the super class object and stored as a tuple.

        :param variables:
        :param values:
        :return: VALUE tuple object
        """
        for var in variables:
            if not is_variable_supported(var):
                raise Exception("Argument not of valid type.")

        for val in values:
            for data_block_value in val:
                if not is_variable_supported(data_block_value):
                    raise Exception("Argument not of valid type.")

        # TODO: check if number of variables matches number of values in each data block

        return tuple.__new__(VALUES, (variables, values))

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is:
        VALUES ( ?v1 ?v2 ) {
            ( v1_value1 v2_value2 )
            ( v1_value2 v2_value2 )
        }

        :return: string
        """
        n3_string = "VALUES ( "
        n3_string += " ".join(map(lambda var: var.n3(), self[0]))
        n3_string += " ) { \n"

        for data_block in self[1]:
            n3_string += "( "
            n3_string += " ".join(map(lambda data_block_value: data_block_value.n3(), data_block))
            n3_string += " )\n"

        n3_string += "}"
        return n3_string


class CONDITIONAL_STATEMENT(STATEMENT):
    """
    Class to store operator details in an object. It extends the
    STATEMENT class, and can be used like it.

    This class is ,however, for internal use cases and shouldn't be used
    directly by the user.
    """

    def __new__(cls, left, operator, *args, state: bool = True):
        """
        Function to create a new object of CONDITIONAL_STATEMENT and store as a tuple.
        No check is provided for the arguments, and should be passed after checking with
        is_variable_supported.

        :param left: left argument for the operator
        :param operator: operator string
        :param args: right arguments for the operator
        :param state: boolean state (negation via "NOT")
        :return: CONDITIONAL_STATEMENT tuple object
        """
        return tuple.__new__(CONDITIONAL_STATEMENT, (left, operator, args, state))

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is:
        1. If there is only one right argument: "?left op ?right"
        2. 2 or more right arguments: "?left op (?right1, ?right2, ?right, ...)"

        :return: string
        """
        n3_string = self[0].n3() + " "
        if not self[3]:
            n3_string += "NOT "
        n3_string += self[1] + " "
        # check if there is only one right arguments for the operator
        if len(self[2]) == 1:
            n3_string += self[2][0].n3()
        else:
            # cover the comma separated arguments with circular brackets.
            n3_string += "( "
            for i in range(len(self[2])):
                n3_string += self[2][i].n3()
                if i < len(self[2]) - 1:
                    n3_string += ", "
            n3_string += " )"

        return n3_string


class PropertyPaths(object):
    """
    Property paths. See https://www.w3.org/TR/sparql11-query/#propertypaths
    """

    class UnaryPropertyPath(tuple):
        def __new__(cls, operator, operator_position: Literal["prefix", "suffix"], elt):
            if operator_position not in ["prefix", "suffix"]:
                raise Exception(f'Wrong operator position "{operator_position}".')

            if not is_variable_supported(elt):
                raise Exception("Argument not of valid type.")

            return tuple.__new__(cls, (operator, operator_position, elt))

        def n3(self):
            operator, operator_position, elt = self

            if operator_position == "prefix":
                return operator + elt.n3()
            elif operator_position == "suffix":
                return elt.n3() + operator

    class VariadicPropertyPath(tuple):
        def __new__(cls, operator, *elts):
            for elt in elts:
                if not is_variable_supported(elt):
                    raise Exception("Argument not of valid type.")

            return tuple.__new__(cls, (operator, elts))

        def n3(self):
            return self[0].join(list(map(lambda elt: elt.n3(), self[1])))

    @classmethod
    def InversePath(cls, elt):
        return cls.UnaryPropertyPath("^", "prefix", elt)

    @classmethod
    def SequencePath(cls, *elts):
        return cls.VariadicPropertyPath("/", *elts)

    @classmethod
    def AlternativePath(cls, *elts):
        return cls.VariadicPropertyPath("|", *elts)

    @classmethod
    def ZeroOrMorePath(cls, elt):
        return cls.UnaryPropertyPath("*", "suffix", elt)

    @classmethod
    def OneOrMorePath(cls, elt):
        return cls.UnaryPropertyPath("+", "suffix", elt)

    @classmethod
    def ZeroOrOnePath(cls, elt):
        return cls.UnaryPropertyPath("?", "suffix", elt)

    # TODO: NegatedPropertySet and group path


class Aggregates(STATEMENT):
    """
    Class used to define Aggregate Functions like MAX, MIN, SUM etc.
    To be used as:
    >> Aggregates.SUM(var1)
    The above statement gives an output of SUM(?var1) where var1 is of type Variable.

    """

    def __new__(cls, fn, statement, params):
        """
        :param fn: This contains the type of Aggregate function as specified in AGGREGATE_FUNCTION_LIST
        :param statement: Statement inside the function, of type Variable
        :return: tuple of (function, statement)
        """
        if not is_variable_supported(statement):
            raise Exception("Statement in aggregate function {} not of acceptable type.".format(fn))
        if fn not in AGGREGATE_FUNCTION_LIST:
            raise Exception("Aggregate Function {} not supported".format(fn))

        return tuple.__new__(Aggregates, (fn, statement, params))

    @staticmethod
    def create_aggregate(function_name):
        """
        Creates a class for the aggregate function
        :param function_name: Aggregate function Name
        :return: Class for the aggregate function
        """

        def new(cls, statement):
            return Aggregates.__new__(cls, function_name, statement, None)

        return type(str(function_name), (Aggregates,), dict(__new__=new))

    def n3(self):
        """
        Function to define n triple format for the object
        >>SUM( ?var1 )
        :rtype: string
        """
        n3_string = self[0] + "( "
        if params := self[2]:
            n3_string += " ".join(params) + " "
        n3_string += self[1].n3() + " )"
        return n3_string


class GROUP_CONCAT(STATEMENT):
    """
    Class used to define GROUP_CONCAT.
    To be used as:
    >> GROUP_CONCAT(var1, ", ")
    The above statement gives an output of GROUP_CONCAT(?var1; SEPARATOR=", ")
    where var1 is of type Variable.
    """

    def __new__(cls, statement, separator):
        """
        :param statement: Statement inside the function, of type Variable
        :param separator: separator string
        :return: tuple of (function, statement)
        """
        if not is_variable_supported(statement):
            raise Exception("Statement in GROUP_CONCAT not of acceptable type.")

        if not isinstance(separator, str):
            raise Exception("Separator is not a string.")

        return tuple.__new__(GROUP_CONCAT, (statement, separator))

    def n3(self):
        """
        Function to define n triple format for the object
        """
        return "GROUP_CONCAT(" + self[0].n3() + '; SEPARATOR="' + self[1] + '")'


class FunctionExpressions(STATEMENT):
    """
    Class used to define Function Expressions like ASC, DESC etc.
    To be used as:
    >> FunctionExpressions.ASC(var1)
    The above statement gives an output of ASC(?var1) where var1 is of type Variable.
    """

    def __new__(cls, fn_expression, *args, state: bool = True):
        """

        :param fn_expression: This contains the type of function expressions as specified in
                                    FUNCTION_EXPRESSION_SUPPORTED_LIST
        :param args: Variables provided as arguments to the function
        :param state: boolean state (negation via "NOT")
        :return: tuple of (function_expression, args)
        """
        for statement in args:
            if not is_variable_supported(statement):
                raise Exception(
                    "Statement {} in function expression {} not of acceptable type.".format(
                        statement, fn_expression
                    )
                )

        if isinstance(fn_expression, str) and not isinstance(fn_expression, URIRef):
            fn_expression = fn_expression.upper()

        if (
            fn_expression not in FUNCTION_EXPRESSION_SUPPORTED_LIST
            and fn_expression not in XPATH_FUNCTIONS
        ):
            raise Exception("Function expression {} not supported".format(fn_expression))

        return tuple.__new__(FunctionExpressions, (fn_expression, args, state))

    @staticmethod
    def create_function_expressions(fn_expression):
        """
        Creates a class for the various types of function expression
        :param fn_expression: Function expression type
        :return: Class fotr the function expression
        """

        def new(cls, *args, state=True):
            return FunctionExpressions.__new__(cls, fn_expression, *args, state=state)

        return type(str(fn_expression), (FunctionExpressions,), dict(__new__=new))

    def n3(self):
        """
        Defines the n3 format for the output as string
        :rtype: str
        """
        n3_string = "" if self[2] else "!"
        n3_string += self[0].n3() + " ( " if is_variable_supported(self[0]) else self[0] + " ( "
        for i in range(len(self[1])):
            n3_string += self[1][i].n3()
            if i < len(self[1]) - 1:
                n3_string += ", "
        n3_string += " )"
        return n3_string


# Initialising all the Aggregate functions
for function in AGGREGATE_FUNCTION_LIST:
    setattr(Aggregates, function, Aggregates.create_aggregate(function))

# Initialising all the function expressions
for function_expression in FUNCTION_EXPRESSION_SUPPORTED_LIST:
    setattr(
        FunctionExpressions,
        function_expression,
        FunctionExpressions.create_function_expressions(function_expression),
    )


class FILTER(STATEMENT):
    """
    Class to apply filter statement in queries. The filter function is used
    as a statement and hence, extends the class STATEMENT.
    Used as follows
    >> FILTER(Operator.LT(var1, var2))
    Output: FILTER ( ?var1 < ?var2 ) .

    It only accepts one parameter which will cover the whole filter.
    """

    def __new__(cls, expression):
        """
        Function to create object of FILTER.
        It accepts only 1 parameter as the expression which is used
        to apply the filter on the query.

        :param expression: expression to be used for filtering.
        :return: FILTER tuple object
        """
        if not is_variable_supported(expression):
            raise Exception("Expression {} in FILTER not of acceptable type".format(expression))

        return tuple.__new__(FILTER, (expression,))

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is "FILTER ( expression )".

        :return: string
        """
        return "FILTER ( " + self[0].n3() + " ) ."


class FILTER_EXISTS(STATEMENT):
    """
    Class to be used by the user, to input FILTER (NOT) EXISTS in the query.
    Usage as follows
    >> FILTER_EXISTS ( (s, p, o), state=True )
    Output: FILTER EXISTS { ?s ?p ?o . } .
    >> FILTER_EXISTS ( (s, p, o), state=False )
    Output: FILTER NOT EXISTS { ?s ?p ?o . } .
    """

    def __new__(cls, *args, state: bool = True):
        """
        Function to create the FILTER_EXISTS object.
        The input is converted to the super class object and stored as a tuple.

        :param args: statements to be used as pattern
        :param state: boolean state (negation via "NOT")
        :return: FILTER_EXISTS tuple object
        """
        statements = []
        for stmt in args:
            # convert the statements to supported format if not already present
            if not is_variable_supported(stmt):
                statements.append(STATEMENT(stmt))
            else:
                statements.append(stmt)

        return tuple.__new__(FILTER_EXISTS, (statements, state))

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is:
        FILTER EXISTS {
            stmt1 .
            stmt2 .
        } .

        :return: string
        """
        n3_string = "FILTER "
        if not self[1]:
            n3_string += "NOT "
        n3_string += "EXISTS { \n"
        n3_string += " \n".join(map(lambda v: v.n3(), self[0]))
        n3_string += " \n} ."
        return n3_string


class BIND(STATEMENT):
    """
    Class to apply bind statement in queries.
    Used as follows
    >> BIND(var1, var2)
    Output: BIND ( ?var1 AS ?var2 ) .
    """

    def __new__(cls, left, expression):
        """
        Function to create object of BIND.
        :param left: variable to bind.
        :param expression: expression to be used for binding.
        :return: BIND tuple object
        """
        if not is_variable_supported(left):
            raise Exception("Variable {} in BIND not of acceptable type".format(expression))

        if not is_variable_supported(expression):
            raise Exception("Expression {} in BIND not of acceptable type".format(expression))

        return tuple.__new__(
            BIND,
            (
                left,
                expression,
            ),
        )

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is "BIND ( left AS expression )".

        :return: string
        """
        return "BIND ( " + self[0].n3() + " AS " + self[1].n3() + " ) ."


class FOR_GRAPH(STATEMENT):
    """
    Class to specify the graph for the statements and tuple in the query.
    This can be used while specifying graph in where, insert, delete, etc.

    This object can be passed as a statement in any function and hence, extends the STATEMENT class.
    Usage:
    >> FOR_GRAPH (
        (s, p, o),
        name=URIRef("graphname")
    )
    Output: GRAPH <graphname> {
        ?s ?p ?o
    }

    Other statements can be passed as arguments.
    The graph is assumed to be default if a name is not provided.
    """

    def __new__(cls, *args, name=None):
        """
        Function to create GRAPH specific statements.
        It can take multiple statements as objects, be it filter, optional, etc.
        The name is advisable to be provided using URIRef.

        :param args: statements to be queried for the specific graph
        :param name: name of graph
        :return: FOR_GRAPH tuple object
        """
        # if name is present, it should be in the supported format
        if name and not is_variable_supported(name):
            raise Exception("GRAPH name not of acceptable type.")

        statements = []
        for stmt in args:
            # convert the statements to supported format if not already present
            if not is_variable_supported(stmt):
                statements.append(STATEMENT(stmt))
            else:
                statements.append(stmt)

        return tuple.__new__(FOR_GRAPH, (name, statements))

    def n3(self):
        """
        Function to provide the n triple format of the object.
        Each triple in its n3() format is:
        GRAPH <name> {
            stmt1 .
            stmt2 .
        } .

        :return: string
        """
        n3_string = ""
        if self[0]:
            n3_string += "GRAPH " + self[0].n3() + " "
        n3_string += "{ \n"

        for var in self[1]:
            n3_string += var.n3() + " \n"

        n3_string += "\n}  ."
        return n3_string


class QueryBuilder:
    """
    Class to build the SPAQRL Query.
    To be used as:
    query = QueryBuilder().SELECT(
            self.var_s,
            x=self.var_o
        ).WHERE(
            (self.var_s, self.var_p, self.var_o)
        ).build()
    Output -> query - "SELECT ?s (?o as ?x)  WHERE { ?s ?p ?o . } "
    """

    class QueryString(str):
        """
        Class to convert the datatype of the query object to string for the query to be used as a nested query
        """

        def __new__(cls, query):
            return str.__new__(cls, query)

        def n3(self):
            return "{\n" + self + "\n}"

    def __init__(self):

        self.query = ""
        self.is_DISTINCT = False
        self.SELECT_variables_direct = []
        self.SELECT_variables_with_alias = {}
        self.INSERT_variables_direct = []
        self.DELETE_variables_direct = []
        self.WHERE_statements = []
        self.GROUP_BY_expressions = []
        self.ORDER_BY_expressions = []
        self.move_to_graph = None
        self.move_from_graph = None
        self.move_silent = False
        self.add_to_graph = None
        self.add_from_graph = None
        self.add_silent = False

        self.limit = None
        self.offset = None

    def SELECT(self, *args, distinct=False, **kwargs):
        """
        Initialise and store variables, bindings for the SELECT statement

        To be used as:
        query = QueryBuilder().SELECT(
            self.var_s,
            x=self.var_o
        ).WHERE(
            (self.var_s, self.var_p, self.var_o)
        ).build()
        Output -> query - "SELECT ?s (?o as ?x)  WHERE { ?s ?p ?o . } "

        :param args: stores the variables that are needed for the SELECT statement
        :param distinct: Boolean to check whether DISTINCT solution modifier to be used or not
        :param kwargs: stores the variables that are needed for the SELECT statement
        :return: self
        """
        self.is_DISTINCT = distinct

        for var in args:
            if isinstance(var, Aggregates):
                raise Exception("Alias not provided for {}".format(var[1].n3()))
            if not is_variable_supported(var):
                raise Exception("Argument not of valid type.")

            self.SELECT_variables_direct.append(var)

        for var_name, var in kwargs.items():
            if not is_variable_supported(var):
                raise Exception("Argument not of valid type.")

            self.SELECT_variables_with_alias[Variable(var_name)] = var

        return self

    def MOVE(
        self, move_from_graph=URIRef("DEFAULT"), move_to_graph=URIRef("DEFAULT"), move_silent=False
    ):
        """
        Initialise variables required for the MOVE query

        To be used as:

        query = QueryBuilder().MOVE(
            move_from_graph=URIRef("default"),
            move_to_graph=URIRef("Graph_1")
        ).build()

        Output -> query - "MOVE DEFAULT TO GRAPH <Graph_1> "
        :param move_from_graph: Source Graph
        :param move_to_graph: Destination Graph
        :param move_silent: Boolean for SILENT Keyword
        :return: self
        """
        if not is_variable_supported(move_from_graph):
            raise Exception("from_graph name not of acceptable type.")
        if not is_variable_supported(move_to_graph):
            raise Exception("to_graph name not of acceptable type.")
        self.move_from_graph = move_from_graph
        self.move_to_graph = move_to_graph
        self.move_silent = move_silent
        return self

    def ADD(
        self, add_from_graph=URIRef("DEFAULT"), add_to_graph=URIRef("DEFAULT"), add_silent=False
    ):
        """
        Initialise variables required for the ADD query

        To be used as:

        query = QueryBuilder().ADD(
            add_from_graph=URIRef("default"),
            add_to_graph=URIRef("Graph_1")
        ).build()

        Output -> query - "ADD DEFAULT TO GRAPH <Graph_1> "

        :param add_from_graph: Source Graph
        :param add_to_graph: Destination Graph
        :param add_silent: Boolean for SILENT Keyword
        :return: self
        """
        if not is_variable_supported(add_from_graph):
            raise Exception("from_graph name not of acceptable type.")
        if not is_variable_supported(add_to_graph):
            raise Exception("to_graph name not of acceptable type.")
        self.add_from_graph = add_from_graph
        self.add_to_graph = add_to_graph
        self.add_silent = add_silent
        return self

    def INSERT(self, *args):
        """
        Initialise variables required for INSERT query

        To be used as:

        query = QueryBuilder().INSERT(
            self.var_s,
            self.var_p,
            self.var_o,
        ).WHERE(
            (self.var_s, self.var_p, self.var_o)
        ).build()

        Output -> query - "INSERT { ?s ?p ?o } WHERE { ?s ?p ?o . } "

        :param args: Objects to be inserted in the INSERT query
        :return: self
        """
        for statement in args:
            if not is_variable_supported(statement):
                self.INSERT_variables_direct.append(STATEMENT(statement))
            else:
                self.INSERT_variables_direct.append(statement)

        return self

    def DELETE(self, *args):
        """
        Initialise variables required for DELETE query

        To be used as:
         query = QueryBuilder().DELETE(
            self.var_s, self.var_p, self.var_o
        ).WHERE(
            (self.var_s, self.var_p, self.var_o),
            (self.var_o, self.var_p2, self.var_v)
        ).build()
        Output -> query - "DELETE { ?s ?p ?o } WHERE { ?s ?p ?o . ?o ?p2 ?v . } "

        :param args: Objects to be inserted in the DELETE query
        :return: self
        """
        for statement in args:
            if not is_variable_supported(statement):
                self.DELETE_variables_direct.append(STATEMENT(statement))
            else:
                self.DELETE_variables_direct.append(statement)

        return self

    def WHERE(self, *args):
        """
        Initialise variables required for WHERE query

        To be used as:
        query = QueryBuilder().SELECT(
            self.var_s,
            x=self.var_o
        ).WHERE(
            (self.var_s, self.var_p, self.var_o)
        ).build()
        Output -> query - "SELECT ?s (?o as ?x)  WHERE { ?s ?p ?o . } "

        :param args: Objects to be inserted in the WHERE query
        :return: self
        """
        for statement in args:
            if not is_variable_supported(statement):
                self.WHERE_statements.append(STATEMENT(statement))
            else:
                self.WHERE_statements.append(statement)

        return self

    def LIMIT(self, value):
        """
        Initialise variables required for LIMIT query

        To be used as:
        query = QueryBuilder().SELECT(
            Variable("s"),
            Variable("p"),
            Variable("o")
        ).WHERE(
            (Variable("s"), Variable("p"), Variable("o"))
        ).LIMIT(
            100
        ).build()
        Output -> query - "SELECT ?s ?p ?o  WHERE { ?s ?p ?o . } LIMIT 100 "

        :param value: value for the LIMIT query
        :return: self
        """
        self.limit = value

        return self

    def OFFSET(self, value):
        """
        Initialise variables required for OFFSET query

        To be used as:
        query = QueryBuilder().SELECT(
            Variable("s"),
            Variable("p"),
            Variable("o")
        ).WHERE(
            (Variable("s"), Variable("p"), Variable("o"))
        ).OFFSET(
            100
        ).build()
        Output -> query - "SELECT ?s ?p ?o  WHERE { ?s ?p ?o . } OFFSET 100 "

        :param value: value for the OFFSET query
        :return: self
        """
        self.offset = value

        return self

    def GROUP_BY(self, *args):
        """
        Initialise variables required for GROUP_BY query

        To be used as:

        query = QueryBuilder().SELECT(
            self.var_o
        ).WHERE(
            (self.var_s, self.var_p, self.var_o)
        ).GROUP_BY(
            self.var_o
        ).build()

        Output -> query - "SELECT ?o  WHERE { ?s ?p ?o . } GROUP BY ?o "

        :param args: Objects required for the GROUP_BY query
        :return: self
        """
        for var in args:
            if is_variable_supported(var):
                self.GROUP_BY_expressions.append(var)
            else:
                raise Exception("Expression passed in ORDER_BY is not valid.")

        return self

    def ORDER_BY(self, *args):
        """
        Initialise variables required for ORDER_BY query

        To be used as:

        query = QueryBuilder().SELECT(
            self.var_o
        ).WHERE(
            (self.var_s, self.var_p, self.var_o)
        ).ORDER_BY(
            self.var_o, FunctionExpressions.ASC(self.var_s)
        ).build()

        Output -> query - "SELECT ?o  WHERE { ?s ?p ?o . } ORDER BY ?o ASC ( ?s ) "

        :param args: Objects required for the ORDER_BY query
        :return: self
        """
        for var in args:
            if is_variable_supported(var):
                self.ORDER_BY_expressions.append(var)
            else:
                raise Exception("Expression passed in ORDER_BY is not valid.")

        return self

    def build_select(self):
        """
        Function to build the SELECT query using the initialised variables according to the SPARQL syntax
        """
        if len(self.SELECT_variables_direct) + len(self.SELECT_variables_with_alias) > 0:
            self.query += "SELECT "

            if self.is_DISTINCT:
                self.query += "DISTINCT "

            for var in self.SELECT_variables_direct:
                self.query += var.n3() + " "

            for var_alias, var_expression in self.SELECT_variables_with_alias.items():
                self.query += "(" + var_expression.n3() + " as " + var_alias.n3() + ") "

            self.query += " \n"

    def build_move(self):
        """
        Function to build the MOVE query using the initialised variables according to the SPARQL syntax
        """
        if self.move_from_graph is not None and self.move_to_graph is not None:
            self.query += "MOVE "
            if self.move_silent:
                self.query += "SILENT "
            if self.move_from_graph.n3().lower() == "<default>":
                self.query += "DEFAULT"
            else:
                self.query += "GRAPH " + self.move_from_graph.n3()
            self.query += " TO "
            if self.move_to_graph.n3().lower() == "<default>":
                self.query += "DEFAULT"
            else:
                self.query += "GRAPH " + self.move_to_graph.n3()
            self.query += " \n"

    def build_add(self):
        """
        Function to build the ADD query using the initialised variables according to the SPARQL syntax
        """
        if self.add_from_graph is not None and self.add_to_graph is not None:
            self.query += "ADD "
            if self.add_silent:
                self.query += "SILENT "
            if self.add_from_graph.n3().lower() == "<default>":
                self.query += "DEFAULT"
            else:
                self.query += "GRAPH " + self.add_from_graph.n3()
            self.query += " TO "
            if self.add_to_graph.n3().lower() == "<default>":
                self.query += "DEFAULT"
            else:
                self.query += "GRAPH " + self.add_to_graph.n3()
            self.query += " \n"

    def build_insert(self):
        """
        Function to build the INSERT query using the initialised variables according to the SPARQL syntax
        """
        if len(self.INSERT_variables_direct) > 0:
            self.query += "INSERT { \n"

            for var in self.INSERT_variables_direct:
                self.query += var.n3() + " "

            self.query += "\n} \n"

    def build_delete(self):
        """
        Function to build the DELETE query using the initialised variables according to the SPARQL syntax
        """
        if len(self.DELETE_variables_direct) > 0:
            self.query += "DELETE { \n"

            for var in self.DELETE_variables_direct:
                self.query += var.n3() + " "

            self.query += "\n} \n"

    def build_where(self):
        """
        Function to build the WHERE query using the initialised variables according to the SPARQL syntax
        """
        if self.move_from_graph is None and self.add_from_graph is None:
            if len(self.WHERE_statements) == 0:
                raise Exception("Query must have at least one WHERE statement.")

            self.query += "WHERE {" + " \n"

            for statement in self.WHERE_statements:
                self.query += statement.n3() + " \n"

            self.query += "}" + " \n"
        else:
            if len(self.WHERE_statements) > 0:
                raise Exception("WHERE unexpected with MOVE/ADD")

    def build_group_by_order_by(self):
        """
        Function to build the GROUP BY and ORDER BY query using the initialised variables according to the SPARQL syntax
        """
        if len(self.GROUP_BY_expressions) > 0:
            self.query += "GROUP BY "
            for var in self.GROUP_BY_expressions:
                self.query += var.n3() + " "
            self.query += "\n"

        if len(self.ORDER_BY_expressions) > 0:
            self.query += "ORDER BY "
            for var in self.ORDER_BY_expressions:
                self.query += var.n3() + " "
            self.query += "\n"

    def build_limit_offset(self):
        """
        Function to build the LIMIT and OFFSET query using the initialised variables according to the SPARQL syntax
        """
        if self.limit:
            self.query += "LIMIT " + str(self.limit) + " \n"

        if self.offset:
            self.query += "OFFSET " + str(self.offset) + " \n"

    def build(self):
        """
        Function to build the query according to the SPARQL syntax
        :return: SPARQL query in str format
        """
        self.build_select()
        self.build_insert()
        self.build_delete()
        self.build_move()
        self.build_add()
        self.build_where()

        self.build_group_by_order_by()
        self.build_limit_offset()

        return QueryBuilder.QueryString(self.query)
