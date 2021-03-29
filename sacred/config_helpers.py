class CMD(str):
    def __new__(CMD, *args, **kw):
        """
            Defines a new CMD config.
            If the command string starts with '/', command not ingredient specific, and will be executed globally (removing the / char)
            If it starts with '.', command has a relative path to the current ing
        :param args:
        :param kw:
        """
        return str.__new__(CMD, *args, **kw)

    def __repr__(self):
        return "{CMD!}" + str.__repr__(self)


class DynamicIngredient(dict):
    def __init__(self, path, *args, **kw):
        """
            Defines a new DynamicIngredient config.
            A DynamicIngredient is automatically imported and added to as a sub-ingredient when a Run is created.
        :param args:
        :param kw:
        """
        self.path = path
        super().__init__(*args, **kw)

    def __repr__(self):
        return "{DI@" + self.path + "}" + dict.__repr__(self)
