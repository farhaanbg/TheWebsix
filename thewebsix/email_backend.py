from django.core.mail.backends.console import EmailBackend as ConsoleEmailBackend


class CleanConsoleEmailBackend(ConsoleEmailBackend):
    def write_message(self, message):
        self.stream.write(message.body)
        self.stream.write('\n')