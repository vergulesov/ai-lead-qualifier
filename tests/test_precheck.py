from app.precheck import message_should_process, call_should_process


def test_noise_message_is_ignored():
    assert message_should_process("Спасибо") is False


def test_substantive_message_is_processed():
    assert message_should_process(
        "Дом новый, площадь 300 метров, хотим начать осенью"
    ) is True


def test_short_call_is_ignored():
    assert call_should_process(10) is False


def test_long_call_is_processed():
    assert call_should_process(180) is True
