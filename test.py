# test_blinker.py
from blinker import signal

def handler(sender):
    print(f"Received signal from {sender}")

my_signal = signal('test')
my_signal.connect(handler)
my_signal.send('test_sender')
