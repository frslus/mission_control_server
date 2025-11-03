import websockets
from websockets.sync.server import serve
import threading
import json
import numpy as np
import sounddevice as sd
from test.MCPTesting import DEFAULT_COMMAND_SET, ServerInterruptMockup


class MainServer:
    """An object representing server.
    :ivar __max_users: the maximal number of clients server can handle at a time
    :type __max_users: int
    :ivar __active_users: an array of references to active users object instances TODO
    :type __active_users: list[Any] TODO
    :ivar __active_threads: a set of threads to stop once the server is shut down
    :type __active_threads: set[threading.Thread]
    :ivar __command_set: a list of commands sent from client to the server
    :type __command_set: list[Callable]"""

    # A reference for running MainServer instance
    MAIN_SERVER = None

    def __init__(self):
        self.STOP_SERVER = threading.Event()
        self.__max_users = 2
        self.__active_users = [None for _ in range(self.__max_users)]
        self.__active_threads = set()
        self.__command_set = DEFAULT_COMMAND_SET
        MainServer.MAIN_SERVER = self

    def initiate_server(self) -> None:
        """This function is called once when the server starts.
        :return None:"""
        print("Server started")
        server_listener = ServerListener()
        server_listener.start()
        self.add_thread(server_listener)
        # for testing purposes only
        server_interrupt_mockup = ServerInterruptMockup(MainServer.MAIN_SERVER)
        server_interrupt_mockup.start()
        self.add_thread(server_interrupt_mockup)

    def main_server_loop(self) -> None:
        """This function is repeated in loop when server is running.
        :return None:"""
        pass

    def close_server(self) -> None:
        """This function is called once when the server shuts down.
        :return None:"""
        self.kill_all_threads()
        for thread in self.__active_threads:
            thread.join()
        print("Server closed")

    def run(self) -> None:
        """The body of the server, consists of initializing function, main loop and closing function.
        :return None:"""
        self.initiate_server()
        while not self.STOP_SERVER.is_set():
            self.main_server_loop()
        self.close_server()

    def add_thread(self, thread):
        """Adds a new active thread."""
        self.__active_threads.add(thread)

    def remove_thread(self, thread):
        """Removes an active thread."""
        if thread in self.__active_threads:
            self.__active_threads.remove(thread)
        else:
            pass

    def kill_all_threads(self):
        """Stops all active threads (most probably during server shutdown)."""
        for thread in self.__active_threads:
            thread.stop()


class ServerListener(threading.Thread):
    """A thread listening for new incoming connections.
    :ivar server_listener: a WebSocket server listening on certain port
    :type server_listener: websockets.sync.server.Server, None"""

    def __init__(self):
        super().__init__()
        self.server_listener = None

    def run(self):
        with serve(user_handler, "localhost", 9000) as server_listener:
            self.server_listener = server_listener
            server_listener.serve_forever()

    def stop(self):
        self.server_listener.shutdown()
        print(f"Thread {self} stopped")


def user_handler(websocket: websockets.sync.server.ServerConnection) -> None:
    """Function called every time a new client is connected. Works in a loop until client disconnects or server shuts down.
    :param websocket: an object representing a connection with one client
    :type websocket: websockets.sync.server.ServerConnection
    :return None:"""
    print("Client connected")
    instruction_list = DEFAULT_COMMAND_SET
    try:
        for message in websocket:
            if MainServer.MAIN_SERVER.STOP_SERVER.is_set():
                raise InterruptedError()
            if isinstance(message, str):
                message = json.loads(message)
                if "command" in message:
                    result = instruction_list[message["command"]](message["data"])
                    response = json.dumps({"command": message["command"], "result": result})
                else:
                    response = json.dumps({"command": -1, "result": None})
                websocket.send(response)
            elif isinstance(message, bytes):
                websocket.send("Sound received")
                sd.play(np.frombuffer(message, dtype='int16'), samplerate=44100)
                sd.wait()
            else:
                raise TypeError(f"Incorrect message type: {type(message)}")
    except websockets.exceptions.ConnectionClosedOK:
        print("Client disconnected correctly")
    except websockets.exceptions.ConnectionClosedError:
        print("Client disconnected incorrectly")
    except InterruptedError:
        print("Disconnected due to server stopping")


def main() -> None:
    control_panel_server = MainServer()
    control_panel_server.run()


if __name__ == "__main__":
    main()
