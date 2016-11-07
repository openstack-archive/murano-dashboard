#    Copyright (c) 2016 AT&T
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import testtools

from muranodashboard.dynamic_ui import yaql_expression


class TestYaqlExpression(testtools.TestCase):
    def setUp(self):
        super(TestYaqlExpression, self).setUp()

        yaql = "$foo"
        string = "test"
        self.yaql_expr = yaql_expression.YaqlExpression(yaql)
        self.str_expr = yaql_expression.YaqlExpression(string)

    def test_overloading(self):
        self.assertEqual("test", self.str_expr.__str__())
        self.assertEqual("$foo", self.yaql_expr.__str__())

        self.assertEqual("YAQL(test)", self.str_expr.__repr__())
        self.assertEqual("YAQL($foo)", self.yaql_expr.__repr__())

    def test_expression(self):
        self.assertEqual("$foo", self.yaql_expr.expression())
        self.assertEqual("test", self.str_expr.expression())

    def test_match(self):
        self.assertFalse(self.str_expr.match(12345))
        self.assertFalse(self.str_expr.match(self.str_expr._expression))
        self.assertTrue(self.yaql_expr.match(self.yaql_expr._expression))
        self.assertFalse(self.yaql_expr.match("$!"))  # YaqlLexicalException
        self.assertFalse(self.yaql_expr.match("$foo("))  # YaqlGrammarException

    def test_evaluate(self):
        self.assertEqual("test", self.str_expr.evaluate())
        self.assertIsNone(self.yaql_expr.evaluate())
