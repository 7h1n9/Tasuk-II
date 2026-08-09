from __future__ import annotations

import argparse
import socket
import socketserver
import threading


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        server = self.server
        target = socket.create_connection(
            (server.target_address, server.target_port),
            timeout=5,
        )
        self.request.settimeout(None)
        target.settimeout(None)

        threads = [
            threading.Thread(target=self._forward, args=(self.request, target), daemon=True),
            threading.Thread(target=self._forward, args=(target, self.request), daemon=True),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        target.close()

    @staticmethod
    def _forward(source: socket.socket, destination: socket.socket) -> None:
        try:
            while True:
                data = source.recv(65536)
                if not data:
                    break
                destination.sendall(data)
        except (ConnectionResetError, OSError):
            pass
        finally:
            try:
                destination.shutdown(socket.SHUT_WR)
            except OSError:
                pass


class ProxyServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, listen_address: str, listen_port: int, target_address: str, target_port: int) -> None:
        self.target_address = target_address
        self.target_port = target_port
        super().__init__((listen_address, listen_port), ProxyHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="TCP proxy for VMware VMnet challenge ports")
    parser.add_argument("--listen-address", required=True)
    parser.add_argument("--listen-port", required=True, type=int)
    parser.add_argument("--target-address", required=True)
    parser.add_argument("--target-port", required=True, type=int)
    args = parser.parse_args()

    with ProxyServer(
        listen_address=args.listen_address,
        listen_port=args.listen_port,
        target_address=args.target_address,
        target_port=args.target_port,
    ) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
