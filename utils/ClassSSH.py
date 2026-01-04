

import time
import asyncssh
from typing import List, AsyncGenerator, Optional
import logging


class AsyncSSHClient:
    def __init__(self, host: str, username: str, password: str, logger: logging.Logger, port: int = 22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.logger = logging.getLogger(f"{logger.name}.{self.__class__.__name__}")
        self.conn: Optional[asyncssh.SSHClientConnection] = None

    async def __aenter__(self):
        '''Установка соединения для контекстного менеджера'''
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        '''Закрытие соединения для контекстного менеджера'''
        await self.close()
        return False

    async def connect(self):
        '''ручное открытие соединения'''
        try:
            self.conn = await asyncssh.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                known_hosts=None  # не проверять ключи
            )
            self.logger.info(f"Успешное подключение к хосту {self.host}")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к хосту {self.host}: {e}")
            raise

    async def close(self):
        '''ручное закрытие соединения'''
        if self.conn:
            self.conn.close()
            await self.conn.wait_closed()
            self.conn = None
            self.logger.info(f"Соединение с хостом {self.host} закрыто")

    async def run_command(self, command: str, streaming: bool = False) -> List[str]:
        """Универсальный метод для выполнения команд, выбирает какой метод использовать
        по умолчанию streaming=False будет выполняться execute_command (одиночный вывод)
        если передать True, то будет execute_command_streaming (потоковый вывод)

        # Обычная команда
        ls_result = await client.run_command("ls")

        # Команда с потоковым выводом
        history_result = await client.run_command("cat ~/.bash_history", streaming=True)
        for line in history_result:
        """
        if streaming:
            lines = []
            async for line in self.execute_command_streaming(command):
                lines.append(line)
            return lines
        else:
            return await self.execute_command(command)

    async def execute_command(self, command: str) -> List[str]:
        """Выполнение команды и возврат всех результатов в списке"""
        await self.connect()
        self.logger.info(f"Выполняю команду: {command}")
        try:
            result = await self.conn.run(command, check=False)
            if result.stderr:
                self.logger.warning(f"Stderr при выполнении команды: {result.stderr.strip()}")
            lines = [line for line in result.stdout.splitlines() if line]
            self.logger.info(lines)
            return lines
        except Exception as e:
            self.logger.error(f"Ошибка выполнения команды '{command}': {e}")
            raise

    async def execute_command_streaming(self, command: str) -> AsyncGenerator[str, None]:
        """Выполнение команды с потоковым выводом построчно"""
        await self.connect()
        self.logger.info(f"Выполняю команду (streaming): {command}")
        try:
            async with self.conn.create_process(command) as process:
                async for line in process.stdout:
                    yield line.rstrip()
        except Exception as e:
            self.logger.error(f"Ошибка выполнения команды: {e}")
            raise