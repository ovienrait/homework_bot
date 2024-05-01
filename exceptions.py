class TokenError(Exception):
    """Не найдены переменные виртуального исключения."""

    pass


class ResponseError(Exception):
    """Получен ответ от API со статусом, отличным от 200."""

    pass
