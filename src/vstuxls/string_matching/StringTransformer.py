# Базовый класс для всех преобразователей строк
class StringTransformer:
    registry = {}

    @classmethod
    def register(cls, transformer_cls):
        # Регистрация подкласса в реестре по его id
        transformer_id = transformer_cls.get_id()
        cls.registry[transformer_id] = transformer_cls

    def transform(self, string: str) -> str:
        raise NotImplementedError('StringTransformer class is intended for subclassing only.')

    @classmethod
    def apply(cls, transformer_id: 'str | callable', string: str) -> str:
        # Получение класса преобразователя по id и применение его к строке
        
        if callable(transformer_id):
            f = transformer_id  # 
            return f(string)
        
        transformer_cls = cls.registry.get(transformer_id)
        if transformer_cls is None:
            raise ValueError(f"No transformer registered for id: {transformer_id}")
        
        transformer = transformer_cls()  # Note: excessive creation for just one call
        return transformer.transform(string)
