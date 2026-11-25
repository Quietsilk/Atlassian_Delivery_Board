import importlib.util
from pathlib import Path
import unittest


def load_server_entrypoint():
    path = Path(__file__).resolve().parents[1] / "server.py"
    spec = importlib.util.spec_from_file_location("ada_server_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ServerSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = load_server_entrypoint()

    def test_loopback_bind_hosts_are_allowed(self):
        for host in ("127.0.0.1", "localhost", "::1"):
            with self.subTest(host=host):
                self.server._validate_bind_host(host)

    def test_external_bind_hosts_are_rejected(self):
        for host in ("0.0.0.0", "192.168.1.10", "example.com"):
            with self.subTest(host=host):
                with self.assertRaises(RuntimeError):
                    self.server._validate_bind_host(host)


if __name__ == "__main__":
    unittest.main()
