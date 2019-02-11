# -*- coding: utf-8 -*-


class QueryParamParserBase(object):
    def parse(self, fields):
        raise NotImplementedError


class UnderlineQueryParamParser(QueryParamParserBase):
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
