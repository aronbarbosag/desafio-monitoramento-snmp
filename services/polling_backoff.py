BASE_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 3600
BACKOFF_MULTIPLIER = 2


def next_poll_interval(consecutive_failures: int) -> int:
    """Intervalo (em segundos) até a próxima tentativa, dado o histórico de
    falhas seguidas de um device.

    Sem falhas (poll com sucesso), volta pro intervalo base. Cada falha
    consecutiva dobra o intervalo (backoff exponencial) até o teto de
    MAX_INTERVAL_SECONDS — assim um device desligado por dias não é sondado a
    cada minuto pra sempre, mas volta ao intervalo base assim que responder.
    """
    if consecutive_failures <= 0:
        return BASE_INTERVAL_SECONDS
    interval = BASE_INTERVAL_SECONDS * (BACKOFF_MULTIPLIER**consecutive_failures)
    return min(interval, MAX_INTERVAL_SECONDS)
