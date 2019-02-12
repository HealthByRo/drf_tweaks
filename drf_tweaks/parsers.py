# -*- coding: utf-8 -*-


class QueryParamParserBase(object):
    def parse(self, fields):
        raise NotImplementedError


class UnderlineQueryParamParser(QueryParamParserBase):
    """
        Parses string like 'user__id,user__city,user__city__name,first_name,job' to dictionary
        """

    def parse(self, fields):
        def create_tree(fields, res=None):
            res = res or {}
            for field in fields:
                parts = field.split("__", 1)
                parts_length = len(parts)
                key = parts[0]
                if key not in res:
                    res[key] = {}
                    res.update({
                        key: create_tree([parts[1]], res[key]) if parts_length > 1 else {}
                    })
                else:
                    res[key].update(create_tree([parts[1]], res[key]) if parts_length > 1 else {})
            return res

        return create_tree(fields)


class BracesQueryParamsParser(QueryParamParserBase):
    """
    Parses string like 'user{id,city{name}, city, first_name}, job' to dictionary
    """

    def parse(self, fields):
        import pyparsing as pp

        fields = '{' + ','.join(fields) + '}'

        simpleString = pp.Combine(pp.Regex(r'[a-zA-Z_]+')).setName("simple string without quotes")

        LBRACE, RBRACE = map(pp.Suppress, "{}")

        jsonString = simpleString

        jsonObject = pp.Forward()
        jsonValue = pp.Forward()
        jsonValue << (jsonString | pp.Group(jsonObject))
        memberDef = pp.Group(jsonString + pp.Optional(jsonValue))
        jsonMembers = pp.delimitedList(memberDef)
        jsonObject << pp.Dict(LBRACE + pp.Optional(jsonMembers) + RBRACE)

        return jsonObject.parseString(fields).asDict()
