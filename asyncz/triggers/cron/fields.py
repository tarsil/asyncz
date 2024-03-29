import re
from calendar import monthrange
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict

from asyncz.triggers.cron.constants import MAX_VALUES, MIN_VALUES
from asyncz.triggers.cron.expressions import (
    AllExpression,
    LastDayOfMonthExpression,
    MonthRangeExpression,
    RangeExpression,
    WeekdayPositionExpression,
    WeekdayRangeExpression,
)

SEPARATOR = re.compile(" *, *")


class BaseField(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: Optional[str] = None
    exprs: Optional[Any] = None
    is_default: Optional[bool] = False
    expressions: Optional[List[Any]] = None
    compilers: Optional[List[Any]] = None
    real: Optional[bool] = False

    def __init__(
        self,
        name: str,
        exprs: Any,
        is_default: Optional[bool] = False,
        compilers: Optional[List[Any]] = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.name = name
        self.is_default = is_default
        self.exprs = exprs
        self.compilers = [AllExpression, RangeExpression]

        if compilers:
            self.compilers += compilers

        self.real: bool = True
        self.compile_expressions(exprs)

    def get_min(self, dateval: datetime):
        return MIN_VALUES[self.name]

    def get_max(self, dateval: datetime):
        return MAX_VALUES[self.name]

    def get_value(self, dateval: datetime):
        return getattr(dateval, self.name)

    def get_next_value(self, dateval: datetime):
        smallest = None
        for expr in self.expressions:
            value = expr.get_next_value(dateval, self)
            if smallest is None or (value is not None and value < smallest):
                smallest = value

        return smallest

    def compile_expressions(self, exprs: Any):
        self.expressions = []

        for expr in SEPARATOR.split(str(exprs).strip()):
            self.compile_expression(expr)

    def compile_expression(self, expr: Any):
        for compiler in self.compilers or []:
            match = compiler.regex.match(expr)
            if match:
                compiled_expr = compiler(**match.groupdict())
                try:
                    compiled_expr.validate_range(self.name)
                except ValueError as e:
                    message = "Error validating expression {!r}: {}".format(expr, e)
                    raise ValueError(message) from e
                self.expressions.append(compiled_expr)
                return

        raise ValueError('Unrecognized expression "{}" for field "{}"'.format(expr, self.name))

    def __eq__(self, other):
        return isinstance(self, self.__class__) and self.expressions == other.expressions

    def __str__(self):
        expr_strings = (str(e) for e in self.expressions)
        return ",".join(expr_strings)

    def __repr__(self):
        return "{}('{}', '{}')".format(self.__class__.__name__, self.name, self)


class WeekField(BaseField):
    def __init__(self, name: str, exprs: Any, is_default: Optional[bool] = False, **kwargs: Any):
        super().__init__(name, exprs, is_default, **kwargs)
        self.real: bool = False

    def get_value(self, dateval: datetime):
        return dateval.isocalendar()[1]


class DayOfMonthField(BaseField):
    def __init__(self, name: str, exprs: Any, is_default: Optional[bool] = False, **kwargs: Any):
        compilers = [WeekdayPositionExpression, LastDayOfMonthExpression]
        super().__init__(name, exprs, is_default, compilers=compilers, **kwargs)

    def get_max(self, dateval: datetime):
        return monthrange(dateval.year, dateval.month)[1]


class DayOfWeekField(BaseField):
    def __init__(self, name: str, exprs: Any, is_default: Optional[bool] = False, **kwargs: Any):
        compilers = [WeekdayRangeExpression]
        super().__init__(name, exprs, is_default, compilers=compilers, **kwargs)
        self.real: bool = False

    def get_value(self, dateval: datetime):
        return dateval.weekday()


class MonthField(BaseField):
    def __init__(self, name: str, exprs: Any, is_default: Optional[bool] = False, **kwargs: Any):
        compilers = [MonthRangeExpression]
        super().__init__(name, exprs, is_default, compilers=compilers, **kwargs)
